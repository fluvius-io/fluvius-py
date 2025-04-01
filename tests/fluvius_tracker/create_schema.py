import asyncio
from fluvius_tracker.model import SQLTrackerConnector, SQLTrackerDataModel


async def db_gen():
    db = SQLTrackerConnector._engine
    async with db.begin() as conn:
        await conn.run_sync(SQLTrackerDataModel.metadata.drop_all)
        await conn.run_sync(SQLTrackerDataModel.metadata.create_all)

asyncio.run(db_gen())
