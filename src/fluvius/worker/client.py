import redis
import arq
import asyncio

from dataclasses import is_dataclass, asdict

from datetime import datetime
from fluvius.error import BadRequestError
from fluvius.data import UUID_GENR, UUID_TYPE
from fluvius.tracker import config as tracker_config
from . import config, logger
from .helper import build_redis_settings
from .tracker import FluviusWorkerTracker, JobStatus


# DEBUG = config.DEBUG
DEBUG = True

class WorkerClient(object):
    ''' Client connects with the workers via:
        - queue_name
        - redis_database
        - redis_server / host / port
    '''

    # CONVENTION NOTE: Class parameters should always wrapped with double underscores (__).
    # ---------------- It is more verbose but easier to read.
    __queue_name__ = None
    __serializers__ = (None, None)
    __redis_settings__ = None
    __tracker__ = None
    __user_manager_class__ = None

    def __init__(self, parent=None, **kwargs):
        self._parent = parent
        self._redis_settings = build_redis_settings(self.__redis_settings__)
        self._tracker = self.validate_tracker(self.__tracker__)
        self._default_settings = dict(
            job_serializer=self.__serializers__[0],
            job_deserializer=self.__serializers__[1]
        )

    def validate_tracker(self, tracker):
        if tracker is None:
            return None

        if not isinstance(tracker, FluviusWorkerTracker):
            raise ValueError(f'Invalid worker tracker: {tracker}')

        return tracker

    @property
    def redis_pool(self):
        return self._redis_pool

    @property
    def queue_name(self):
        return self.__queue_name__

    async def unwrap_job_data(self, job):
        data = {}

        if isinstance(job, arq.jobs.Job):
            queue_name = job._queue_name
            data = asdict(await job.info())
            data["_id"] = UUID_TYPE(job.job_id)
            data.pop('job_id')
            data["queue_name"] = queue_name
        else:
            raise ValueError(f'Invalid job handle: {job}')

        return data


    def get_job(self, job_id):
        return arq.jobs.Job(
            job_id=job_id.hex,
            redis=self.redis_pool,
            _deserializer=default_deserializer
        )

    async def cancel_job(self, job_id):
        job_handle = None
        if self._tracker:
            job_handle = await self._tracker.fetch_entry(tracker_config.WORKER_JOB_TABLE, job_id)

            if job_handle is None or job_handle.job_status != JobStatus.RECEIVED:
                raise BadRequestError(
                    errcode=400422,
                    message="Cannot cancel this job. "
                    f"Current job status: {job_handle.job_status.label}."
                )

        try:
            await self.get_job(job_id).abort()
        except (asyncio.TimeoutError, arq.jobs.SerializationError):
            DEBUG and logger.info("[WORKER-CLIENT] Job Canceled: {}".format(job_id))
            if job_handle is not None:
                await self._tracker.update_entry(
                    job_handle,
                    job_status=JobStatus.CANCELED,
                    finish_time=timestamp()
                )
            return True

        return False

    async def register_job(self, job, **options):
        if not self._tracker:
            return job

        ''' See: https://arq-docs.helpmanual.io/#arq.connections.ArqRedis.enqueue_job
        '''
        data = await self.unwrap_job_data(job)
        data["defer_time"] = options.get('_defer_until', None)
        data["job_status"] = JobStatus.SUBMITTED
        data["job_progress"] = -1
        data["job_try"] = 0
        await self._tracker.add_entry(tracker_config.WORKER_JOB_TABLE, **data)
        return job

    async def enqueue_job(self, job_name, *args, **options):
        if not hasattr(self, "_redis_pool"):
            await self.open_pool()

        job_id = UUID_GENR().hex

        try:
            job = await self.redis_pool.enqueue_job(job_name, *args, _job_id=job_id, **options)
        except (
            AttributeError,
            ConnectionResetError,
            asyncio.TimeoutError,
        ) as exc:
            logger.warning('Failed to push task [%s] into queue. Retry. [%s] ', job_name, exc)
            await self.reset_pool()
            job = await self.redis_pool.enqueue_job(job_name, *args, _job_id=job_id, **options)

        return await self.register_job(job, **options)

    async def reset_pool(self):
        await self.close_pool()
        await self.open_pool()

    async def open_pool(self, **kwargs):
        if hasattr(self, "_redis_pool"):
            raise ValueError('Redis pool is already opened.')

        self._redis_pool = await arq.create_pool(
            self._redis_settings,
            **self._default_settings,
            **kwargs
        )

    async def close_pool(self):
        if not hasattr(self, "_redis_pool"):
            return

        await self.redis_pool.close()
        delattr(self, "_redis_pool")

    async def reload_worker(self, **kwargs):
        handle = await self.enqueue_job(
            "reload_worker_cron", _queue_name=self.queue_name, **kwargs
        )
        DEBUG and logger.info("[CLIENT] Reload worker")
        return handle

    async def send(self, entrypoint, *args, **kwargs):
        DEBUG and logger.info("[CLIENT-SEND] %s@%s", entrypoint, self.queue_name)
        return await self.enqueue_job(entrypoint, *args, _queue_name=self.queue_name, **kwargs)

    async def request(self, entrypoint, *args, **kwargs):
        handle = await self.send(entrypoint, *args, **kwargs)
        result = await handle.result()
        DEBUG and logger.info("[CLIENT-RESULT] %s@%s => %s", entrypoint, self.queue_name, result)
        return result


