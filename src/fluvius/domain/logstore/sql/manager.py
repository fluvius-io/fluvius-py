from types import SimpleNamespace
from fluvius.data import DataFeedManager, data_query

from fluvius.domain import config
from .model import DomainLogConnector
from ..base import DomainLogStore


class SQLDomainLogManager(DataFeedManager):
    __connector__ = DomainLogConnector
    __auto_model__ = True


class SQLDomainLogStore(SQLDomainLogManager, DomainLogStore):
    def _add_entry(self, resource, data):
        return self.insert_data(resource, data.serialize())
