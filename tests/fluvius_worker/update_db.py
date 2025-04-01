import asyncio
from fluvius_worker import FluviusWorker, logger
from fluvius_worker.tracker import JobTrackerConnector, JobTrackerDataModel


async def db_gen():
    db = JobTrackerConnector._engine
    async with db.begin() as conn:
        await conn.run_sync(JobTrackerDataModel.metadata.drop_all)
        await conn.run_sync(JobTrackerDataModel.metadata.create_all)

asyncio.run(db_gen())
