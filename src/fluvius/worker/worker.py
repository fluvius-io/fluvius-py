import os
import arq
import asyncio
import functools
import logging.config
import socket

from time import time
from asyncio import get_event_loop
from datetime import datetime, timedelta
from types import SimpleNamespace
from dataclasses import dataclass

from arq.cron import CronJob, cron as arq_cron
from arq.logs import default_log_config
from arq.worker import func as arq_func

from fluvius.helper import assert_, camel_to_lower_underscore, when
from fluvius.helper.timeutil import timestamp
from fluvius.tracker import config as tracker_config
from fluvius.domain.context import DomainTransport
from . import config, event, logger
from .serializer import default_deserializer, default_serializer
from .helper import build_redis_settings
from .tracker import JobStatus, WorkerStatus


# @TODO: Remove this.
# logging.config.dictConfig(default_log_config(True))

WORKER_HEART_BEAT_INTERVAL_SECONDS = 30
PING_EXPIRATION = timedelta(seconds=3)
PING_TIMEOUT = 5
PING_MAX_TRIES = 1
ATTR_CRON = '__cron_params__'
ATTR_TASK = '__task_params__'
ATTR_TRACKER = '__track_params__'


def export_task(func_or_none=None, **params):
    ''' Export a job function

        :param name: name for function, if None, ``coroutine.__qualname__`` is used
        :param keep_result: duration to keep the result for, if 0 the result is not kept
        :param keep_result_forever: whether to keep results forever, if None use Worker default, wins over ``keep_result``
        :param timeout: maximum time the job should take
        :param max_tries: maximum number of tries allowed for the function, use 1 to prevent retrying
    '''
    def _decorator(func):
        params.setdefault('name', func.__name__)
        setattr(func, ATTR_TASK, params)
        return func

    if func_or_none is not None:
        return _decorator(func_or_none)

    return _decorator


def export_cron(func_or_none=None, **params):
    ''' Export a cron job, eg. it should be executed at specific times.

        Workers will enqueue this job at or just after the set times. If ``unique`` is true (the default) the
        job will only be run once even if multiple workers are running.

        :param name: name of the job, if None, the name of the coroutine is used
        :param month: month(s) to run the job on, 1 - 12
        :param day: day(s) to run the job on, 1 - 31
        :param weekday: week day(s) to run the job on, 0 - 6 or mon - sun
        :param hour: hour(s) to run the job on, 0 - 23
        :param minute: minute(s) to run the job on, 0 - 59
        :param second: second(s) to run the job on, 0 - 59
        :param microsecond: microsecond(s) to run the job on,
            defaults to 123456 as the world is busier at the top of a second, 0 - 1e6
        :param run_at_startup: whether to run as worker starts
        :param unique: whether the job should only be executed once at each time (useful if you have multiple workers)
        :param job_id: ID of the job, can be used to enforce job uniqueness, spanning multiple cron schedules
        :param timeout: job timeout
        :param keep_result: how long to keep the result for
        :param keep_result_forever: whether to keep results forever
        :param max_tries: maximum number of tries for the job
    '''
    def _decorator(func):
        params.setdefault('name', func.__name__)
        setattr(func, ATTR_CRON, params)
        return func

    if func_or_none is not None:
        return _decorator(func_or_none)

    return _decorator


def tracker_params(**params):
    ''' Settings for task tracker '''

    def _decorator(func):
        setattr(func, ATTR_TRACKER, params)
        return func
    return _decorator



class FluviusWorker(arq.Worker):
    _functions = tuple()
    _cron_jobs = tuple()
    _startup_hooks = tuple()
    _shutdown_hooks = tuple()
    on_startup = None
    on_shutdown = None

    # CONVENTION NOTE: Class parameters should always wrapped with double underscores (__).
    # ---------------- It is more verbose but easier to read.
    __queue_name__ = None
    __serializers__ = (None, None)
    __redis_settings__ = None    # See: https://arq-docs.helpmanual.io/#module-arq.connections
    __tracker__ = None
    __user_manager_class__ = None
    __downstream_clients__ = tuple()


    def __init__(self, **kwargs):
        '''
        queue_name – queue name to get jobs from
        cron_jobs – list of cron jobs to run, use arq.cron.cron() to create them
        redis_settings – settings for creating a redis connection
        redis_pool – existing redis pool, generally None
        burst – whether to stop the worker once all jobs have been run
        on_startup – coroutine function to run at startup
        on_shutdown – coroutine function to run at shutdown
        max_jobs – maximum number of jobs to run at a time
        job_timeout – default job timeout (max run time)
        keep_result – default duration to keep job results for
        poll_delay – duration between polling the queue for new jobs
        queue_read_limit – the maximum number of jobs to pull
            from the queue each time it’s polled; by default it equals max_jobs
        max_tries – default maximum number of times to retry a job
        health_check_interval – how often to set the health check key
        health_check_key – redis key under which health check is set
        retry_jobs – whether to retry jobs on Retry or CancelledError or not
        max_burst_jobs – the maximum number of jobs to process in burst mode (disabled with negative values)
        job_serializer – a function that serializes Python objects to bytes, defaults to pickle.dumps
        job_deserializer – a function that deserializes bytes into Python objects, defaults to pickle.loads
        '''
        self._redis_settings = build_redis_settings(self.__redis_settings__)
        self._tracker = self.validate_tracker(self.__tracker__)
        self._export_functions, self._export_cron_jobs = self._gather_exports()
        self._last_heart_beat = time() - WORKER_HEART_BEAT_INTERVAL_SECONDS
        self._downstream_clients = dict(self._init_clients())

        ctx = {"queue_name": self.__queue_name__, **self._downstream_clients}

        super().__init__(ctx=ctx, **self.build_settings(**kwargs))

    def _gather_exports(self):
        functions = []
        cron_jobs = []

        for func_name in dir(self):
            if func_name in ('pool',):
                continue

            func = getattr(self, func_name)
            if not callable(func):
                continue

            if hasattr(func, ATTR_TASK):
                functions.append(func)

            if hasattr(func, ATTR_CRON):
                cron_jobs.append(func)

        return tuple(functions), tuple(cron_jobs)

    def _init_clients(self):
        for client_cls in self.__downstream_clients__:
            client = client_cls(self)
            key = camel_to_lower_underscore(client_cls.__name__)
            if self.__queue_name__ == client.__queue_name__:
                raise ValueError('Server and client must not in the same queue.')

            yield key, client

    def validate_tracker(self, tracker):
        from .tracker import FluviusWorkerTracker

        if tracker is None:
            return None

        if not isinstance(tracker, FluviusWorkerTracker):
            raise ValueError(f'Invalid worker tracker: {tracker}')

        return tracker


    def _task_wrap(self, fspec):
        ''' See: https://github.com/python-arq/arq/blob/main/arq/worker.py#L60
                 - class Function(...)
                 - def func(...)
        '''
        if callable(fspec):
            func = fspec
        else:
            func = getattr(self, fspec)

        task_params = getattr(func, ATTR_TASK, {'name': func.__name__})
        if self._tracker:
            track_params = getattr(func, ATTR_TRACKER, {})
            func = self._tracker.decorate_job(func, **track_params)

        return arq_func(func, **task_params)

    def _cron_wrap(self, fspec):
        ''' See: https://github.com/python-arq/arq/blob/main/arq/worker.py#L60
                 - class Function(...)
                 - def func(...)
        '''
        if callable(fspec):
            func = fspec
        else:
            func = getattr(self, fspec)

        cron_params = getattr(func, ATTR_CRON, {'name': func.__name__})
        if self._tracker:
            track_params = getattr(func, ATTR_TRACKER, {})
            func = self._tracker.decorate_job(func, **track_params)

        return arq_cron(func, **cron_params)


    @export_task(timeout=PING_TIMEOUT, max_tries=PING_MAX_TRIES)
    async def _ping(self, ctx, upstream_time, upstreams: tuple[str]=tuple()):
        queue_name = self.__queue_name__
        if queue_name in upstreams:
            raise ValueError(f'Loop back detected: {queue_name}')

        response = {queue_name: (time() - upstream_time,)}
        upstreams += (queue_name, )

        for name, client in self._downstream_clients.items():
            start = time()
            handle = await client.send('_ping', start, upstreams, _expires=PING_EXPIRATION)

            try:
                result = await handle.result()
            except asyncio.exceptions.CancelledError:
                result = {client.__queue_name__: (-1,)}

            elapsed = time() - start
            response.update({f"{queue_name} > {k}": v + (elapsed,) for k, v in result.items()})

        return response


    def validate_cron_jobs(self):
        return tuple(self._cron_wrap(func) for func in self._cron_jobs + self._export_cron_jobs)

    def validate_functions(self):
        return tuple(self._task_wrap(func) for func in self._functions + self._export_functions)

    def build_settings(self, **kwargs):
        startup_hooks = (self._tracker_checkin, self.on_startup, kwargs.pop('on_startup', None)) + self._startup_hooks
        shutdown_hooks = (self._tracker_checkout, self.on_shutdown, kwargs.pop('on_shutdown', None)) + self._shutdown_hooks
        return dict(
            job_completion_wait=3,
            queue_name=self.__queue_name__,
            job_serializer=self.__serializers__[0],
            job_deserializer=self.__serializers__[1],
            cron_jobs=self.validate_cron_jobs(),
            functions=self.validate_functions(),
            redis_settings=self._redis_settings,
            on_startup=self.setup_startup_hooks(*startup_hooks),
            on_shutdown=self.setup_shutdown_hooks(*shutdown_hooks),
            **kwargs
        )


    async def fetch_cron_jobs(self):
        return []

    @classmethod
    def task(cls, func_or_none=None, /, **kwargs):
        def _decorator(func):
            ''' This decorator add an arq.Function object to the list to be registered later
                using [arq.Worker > functions] attributes.
            '''
            cls._functions += (export_task(**kwargs)(func),)
            return func

        if func_or_none is not None:
            return _decorator(func_or_none)

        return _decorator

    @classmethod
    def cron(cls, func_or_none=None, /, **kwargs):
        ''' See: https://github.com/python-arq/arq/blob/main/arq/cron.py#L128
        '''

        def _decorator(func):
            cls._cron_jobs += (export_cron(**kwargs)(func),)
            return func

        if func_or_none is not None:
            return _decorator(func_or_none)

        return _decorator

    @classmethod
    def tasks(cls, *func_iter, **kwargs):
        task_decorator = cls.task(**kwargs)
        return tuple(task_decorator(func) for func in func_iter)

    @classmethod
    def startup(cls, func_or_none):
        ''' Startup hook.
            NOTE: cannot name this as on_startup since it will be overwritten
            by arq upon receiving [on_startup/on_shutdown] parameter.
        '''

        def _decorator(func):
            cls._startup_hooks += (func,)
            return func

        if func_or_none is not None:
            return _decorator(func_or_none)

        return _decorator

    async def shutdown(self, ctx):
        ''' Shutdown hook. '''
        def _decorator(func):
            cls._shutdown_hooks += (func,)
            return func

        if func_or_none is not None:
            return _decorator(func_or_none)

        return _decorator

    def setup_startup_hooks(self, *hooks):
        async def on_startup(ctx):
            ctx["app"] = self
            results = []
            for hook in filter(None, hooks):
                results.append(await hook(ctx))

            for _, recv in event.on_startup.send(self, ctx=ctx):
                await when(recv)

            return results

        return on_startup

    def setup_shutdown_hooks(self, *hooks):
        async def on_shutdown(ctx):
            results = []
            for hook in filter(None, hooks):
                results.append(await hook(ctx))

            for _, recv in event.on_shutdown.send(self, ctx=ctx):
                await when(recv)

            return results

        return on_shutdown

    async def _tracker_checkin(self, ctx):
        ''' Using worker instance as app instead of ctx dictionary
        '''
        if not self._tracker:
            return

        # self._tracker.connect()
        self._handle = await self._tracker.add_entry(
            tracker_config.ARQ_WORKER_TABLE,
            hostname=socket.gethostname(),
            start_time=timestamp(),
            queue_name=self.__queue_name__,
            pid=os.getpid(),
            status=WorkerStatus.STARTED
        )

        ctx["worker_id"] = self._handle._id


    async def _tracker_checkout(self, ctx):
        if not hasattr(self, '_handle'):
            return

        await self._tracker.update_entry(
            self._handle,
            status=WorkerStatus.STOPPED,
            stop_time=timestamp(),
            jobs_complete = self.jobs_complete,
            jobs_failed = self.jobs_failed,
            jobs_retried = self.jobs_retried,
            jobs_queued = len(self.tasks)
        )

    async def record_health(self) -> None:
        await super().record_health()

        now_ts = time()
        if now_ts - self._last_heart_beat < WORKER_HEART_BEAT_INTERVAL_SECONDS:
            return

        self._last_heart_beat = now_ts
        if hasattr(self, '_handle'):
            await self._tracker.update_entry(
                self._handle,
                status=WorkerStatus.RUNNING,
                heart_beat=timestamp(),
                jobs_complete = self.jobs_complete,
                jobs_failed = self.jobs_failed,
                jobs_retried = self.jobs_retried,
                jobs_queued = len(self.tasks)

            )


class SanicFluviusWorker(FluviusWorker):
    def listener(self, hook):
        evt_signal = event.SANIC_HOOK_EVENT_MAP[hook]

        def _decorator(func):
            @functools.wraps(func)
            def sanic_wrapper(sender, ctx):
                '''make sure that the handler call the function
                according to Sanic interface
                '''
                return func(sender, loop=get_event_loop())

            evt_signal.connect(sanic_wrapper, sender=self, weak=False)
            return func

        return _decorator
