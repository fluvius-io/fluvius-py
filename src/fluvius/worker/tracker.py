import traceback
import asyncio
import functools
from types import SimpleNamespace
from fluvius.data import exceptions, UUID_GENF, UUID_TYPE
from fluvius.helper.timeutil import timestamp
from fluvius.tracker import SQLTrackerManager, JobStatus, WorkerStatus, config as tracker_config
from fluvius.error import BadRequestError

from . import config, logger

COLLECT_TRACEBACK = config.COLLECT_TRACEBACK

def format_uuid(_id):
    if isinstance(_id, UUID_TYPE):
        return _id

    if ':' in _id:
        return UUID_GENF(_id)

    return UUID_TYPE(_id)


class FluviusWorkerTracker(SQLTrackerManager):
    def progress_updater(self, job_handle):
        async def _update_progress(progress: float, message: str):
            return await self.update_entry(
                job_handle,
                job_progress=float(progress),
                job_message=str(message)
            )

        return _update_progress

    def decorate_job(self, func, do_not_track=False):
        if do_not_track:
            return func

        if not asyncio.iscoroutinefunction(func):
            raise BadRequestError('W00.201', f'Function is not a coroutine: {func}')

        async def register_job_handle(context, *args, **kwargs):
            try:
                job_handle = await self.fetch_entry(tracker_config.WORKER_JOB_TABLE, format_uuid(context.job_id))
                assert job_handle.worker_id is None, "Job already registered by another worker."
                return await self.update_entry(
                    job_handle,
                    err_message="",
                    job_progress=0,
                    job_status=JobStatus.RECEIVED,
                    start_time=timestamp(),
                    worker_id=context.worker_id,
                )
            except (exceptions.ItemNotFoundError, ValueError):
                logger.info('Job entry has not been registered by client [%s = %s].', func.__name__, context.job_id)
                job_handle = await self.add_entry(tracker_config.WORKER_JOB_TABLE,
                    _id=format_uuid(context.job_id),
                    args=args,
                    kwargs=kwargs,
                    enqueue_time=context.enqueue_time,
                    function=func.__name__,
                    job_progress=0,
                    job_status=JobStatus.RECEIVED,
                    job_try=context.job_try,
                    queue_name=context.app.queue_name,
                    score=context.score,
                    start_time=timestamp(),
                    worker_id=context.worker_id,
                )

                return job_handle


        @functools.wraps(func)
        async def wrapper(ctx, *args, **kwargs):
            context = SimpleNamespace(**ctx)
            job_handle = await register_job_handle(context, *args, **kwargs)
            context.update_progress = self.progress_updater(job_handle)

            try:
                result = await func(context, *args, **kwargs)
            except asyncio.exceptions.CancelledError as e:
                data = await self.fetch_entry(tracker_config.WORKER_JOB_TABLE, job_handle._id)
                if data.job_status != JobStatus.CANCELED:
                    await self.update_entry(job_handle,
                        job_status=JobStatus.CANCELED,
                        job_try=context.job_try,
                        err_message=str(e if not hasattr(e, 'message') else e.message)
                    )
                    logger.info('Job cancelled but status not updated correctly.')
                raise
            except (TimeoutError, Exception) as e:
                tb = traceback.format_exc() if COLLECT_TRACEBACK else None

                await self.update_entry(job_handle,
                    job_status=JobStatus.ERROR,
                    job_try=context.job_try,
                    finish_time=timestamp(),
                    err_message=str(e if not hasattr(e, 'message') else e.message),
                    err_trace=tb
                )
                raise

            await self.update_entry(job_handle,
                job_status=JobStatus.SUCCESS,
                finish_time=timestamp(),
                job_try=context.job_try,
                job_progress=100,
                job_message="",
                result=f"{str(result):.250}" if result else None
            )
            return result

        return wrapper


SQLWorkTracker = FluviusWorkerTracker(None)
