import asyncio
from fluvius_worker import FluviusWorker, logger, SQLWorkTracker, export_task, export_cron


class WorkerSample(FluviusWorker):
    namespace = 'worker-sample'
    tracker = SQLWorkTracker

    @export_cron(second=tuple(range(1, 60, 2)))
    async def sample_cron(self, ctx, *args, **kwargs):
        logger.warning('SAMPLE CRON: ARGS: %s KWARGS: %s', args, kwargs)
        logger.warning("CONTEXT: %s", ctx)
        return "sample_cron"


@WorkerSample.task
async def hello_world(ctx, *args, **kwargs):
    logger.warning('HELLO WORLD: ARGS: %s KWARGS: %s', args, kwargs)
    logger.warning("CONTEXT: %s", ctx)
    await asyncio.sleep(1.0)
    await ctx.update_progress(50, "half-way ...")
    await asyncio.sleep(1.0)
    return "HELLO"

@WorkerSample.cron(second=tuple(range(1, 60, 5)))
async def hello_world(ctx, *args, **kwargs):
    logger.warning('HELLO WORLD: ARGS: %s KWARGS: %s', args, kwargs)
    logger.warning("CONTEXT: %s", ctx)
    await ctx.update_progress(50, "half-way ...")
    return "HELLO"

worker = WorkerSample()
worker.run()
