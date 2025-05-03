import asyncio

from fluvius.worker import logger, SQLWorkTracker, export_task, export_cron, DomainWorker
from object_domain.domain import ObjectDomain
from object_domain.storage import PeopleEconomistResource, populate_fixture_data

NS = 'cqrs-worker-sample'

class OBJDM2(ObjectDomain):
    __namespace__ = 'object-domain-no-2'


class DomainWorkerSample(DomainWorker):
    __queue_name__ = NS
    __tracker__ = SQLWorkTracker
    __domains__ = (ObjectDomain, OBJDM2)


@DomainWorkerSample.task
async def hello_world(ctx, *args, **kwargs):
    logger.info('HELLO WORLD: ARGS: %s KWARGS: %s', args, kwargs)
    logger.info("CONTEXT: %s", ctx)
    await asyncio.sleep(1.0)
    await ctx.update_progress(50, "half-way ...")
    await asyncio.sleep(1.0)
    return "HELLO"

worker = DomainWorkerSample()
worker.run()


