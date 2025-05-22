import traceback
import functools

from asyncio.exceptions import CancelledError
from types import SimpleNamespace
from dataclasses import asdict, is_dataclass

from fluvius.data import DataAccessManagerBase, UUID_GENR
from fluvius.helper.timeutil import timestamp
from .model import SQLTrackerConnector
from . import config, logger

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


class SQLTrackerManager(DataAccessManagerBase):
    __connector__ = SQLTrackerConnector
    __automodel__ = True

    def __init_subclass__(cls):
        super().__init_subclass__()

    async def add_entry(self, resource, **data):
        data['_id'] = UUID_GENR()
        await self.connector.insert(resource, data)
        return self._wrap_model(resource, data)

    async def update_entry(self, record, **updates):
        resource = self.lookup_resource(record)
        return await self.connector.update_one(resource, updates, identifier=record._id)

    async def fetch_entry(self, resource, handle_id):
        item = await self.connector.find_one(resource, identifier=handle_id)
        return self._wrap_model(resource, item)


class SQLTracker(SQLTrackerManager):
    ''' @TODO: This section need performance review since it starts a new transaction
        and a few round trips to the database for each action.
    '''
    pass
