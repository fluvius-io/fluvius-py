import traceback
import functools

from asyncio.exceptions import CancelledError
from types import SimpleNamespace
from dataclasses import asdict, is_dataclass

from fluvius.data import DataFeedManager
from fluvius.helper.timeutil import timestamp
from fluvius_tracker import config, logger
from .model import SQLTrackerConnector

COLLECT_TRACEBACK = config.COLLECT_TRACEBACK


class TrackerInterface(object):
    async def add_entry(self, tracker_name, **kwargs):
        logger.info('[JOB TRACKER] add_entry[%s]: %s', tracker_name, kwargs)
        return SimpleNamespace(**kwargs)

    async def update_entry(self, handle, **kwargs):
        logger.info('[JOB TRACKER] update_entry [%s]: %s', handle, kwargs)
        return handle

    async def fetch_entry(self, tracker_name, handle_id):
        logger.info('[JOB TRACKER] fetch[%s]: %s', tracker_name, handle_id)
        return SimpleNamespace(_id=handle_id)



class NullTracker(TrackerInterface):
    pass


class SQLTrackerManager(DataFeedManager):
    __connector__ = SQLTrackerConnector

    async def add_entry(self, resource, **data):
        record = self.create(resource, **data)
        backend = self.get_resource(resource)

        async with self.transaction():
            await backend.insert_record(record)

        return record

    async def update_entry(self, entry, **kwargs):
        backend = self.get_record_resource(entry)
        async with self.transaction(label='update'):
            handle = await backend.fetch(identifier=entry._id)
            await backend.update_record(handle, **kwargs)
            return handle

    async def fetch_entry(self, resource, handle_id):
        backend = self.get_resource(resource)
        async with self.transaction(label='update'):
            return await backend.fetch(identifier=handle_id)


class SQLTracker(SQLTrackerManager):
    ''' @TODO: This section need performance review since it starts a new transaction
        and a few round trips to the database for each action.
    '''
    pass
