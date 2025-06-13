import traceback
import functools

from asyncio.exceptions import CancelledError
from types import SimpleNamespace
from dataclasses import asdict, is_dataclass

from fluvius.data import DataAccessManagerBase, UUID_GENR, BackendQuery
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

    async def add_entry(self, model_name, **data):
        data['_id'] = UUID_GENR()
        await self.connector.insert(model_name, data)

        model_cls = self.lookup_model(model_name)
        return self._wrap_model(model_cls, data)

    async def update_entry(self, record, **updates):
        model_name = self.lookup_record_model(record)
        q = BackendQuery.create(identifier=record._id)
        return await self.connector.update_one(model_name, q, **updates)

    async def fetch_entry(self, model_name, handle_id):
        q = BackendQuery.create(identifier=handle_id)
        item = await self.connector.find_one(model_name, q)

        model_cls = self.lookup_model(model_name)
        return self._wrap_model(model_cls, item)


class SQLTracker(SQLTrackerManager):
    ''' @TODO: This section need performance review since it starts a new transaction
        and a few round trips to the database for each action.
    '''
    pass
