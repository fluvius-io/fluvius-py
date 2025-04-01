import asyncio

from fluvius_worker import logger, SQLWorkTracker, export_task, export_cron, DomainWorker
from object_example.domain import ObjectDomain
from object_example.storage import PeopleEconomistResource, populate_fixture_data

NS = 'cqrs-worker-sample'

class OBJDM2(ObjectDomain):
    __domain__ = 'object-domain-no-2'


class DomainWorkerSample(DomainWorker):
    queue_name = NS
    tracker = SQLWorkTracker
    domains = (ObjectDomain, OBJDM2)

    # @export_cron(second=tuple(range(1, 60, 2)))
    # async def sample_cron(self, ctx, *args, **kwargs):
    #     logger.info('SAMPLE CRON: ARGS: %s KWARGS: %s', args, kwargs)
    #     logger.info("CONTEXT: %s", ctx)
    #     return "sample_cron"


@DomainWorkerSample.task
async def hello_world(ctx, *args, **kwargs):
    logger.info('HELLO WORLD: ARGS: %s KWARGS: %s', args, kwargs)
    logger.info("CONTEXT: %s", ctx)
    await asyncio.sleep(1.0)
    await ctx.update_progress(50, "half-way ...")
    await asyncio.sleep(1.0)
    return "HELLO"

# @DomainWorkerSample.cron(second=tuple(range(1, 60, 5)))
# async def hello_world(ctx, *args, **kwargs):
#     logger.info('HELLO WORLD: ARGS: %s KWARGS: %s', args, kwargs)
#     logger.info("CONTEXT: %s", ctx)
#     await ctx.update_progress(50, "half-way ...")
#     return "HELLO"


# async def main():
worker = DomainWorkerSample()
worker.run()


