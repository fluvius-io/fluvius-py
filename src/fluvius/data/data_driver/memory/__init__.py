import os
import pickle

from contextlib import asynccontextmanager
from fluvius.data import identifier, logger
from fluvius.data.exceptions import ItemNotFoundError
from fluvius.data.query import BackendQuery

from ..base import DataDriver


def query_resource(store, q: BackendQuery):
    match_attrs = {}

    if q.where:
        match_attrs.update(q.where)

    if q.scope:
        match_attrs.update(q.scope)

    if q.identifier:
        match_attrs['_id'] = q.identifier

    def _match(item):
        try:
            return all(getattr(item, k, None) == v for k, v in match_attrs.items())
        except AttributeError:
            return False

    return filter(_match, store.values())


class InMemoryDriver(DataDriver):
    __filepath__ = None

    def __init_subclass__(cls):
        cls._MEMORY_STORE = {}

    @asynccontextmanager
    async def transaction(self, transaction_id=None):
        yield self
        self.commit()

    @classmethod
    def _get_memory(self, resource):
        store = self._MEMORY_STORE
        if resource not in store:
            store[resource] = {}
        return store[resource]

    async def find(self, resource, query, meta=None):
        store = self._get_memory(resource)
        items = list(query_resource(store, query))

        if meta is not None:
            meta.update({
                "total": len(store),
                "limit": query.limit,
                "offset": query.offset,
                "count": len(items)
            })
        return items

    find_all = find
    query = find

    async def find_one(self, resource, query):
        store = self._get_memory(resource)
        result = query_resource(store, query)

        try:
            item = next(result)
        except StopIteration:
            logger.info('STORAGE: %s', store)
            raise ItemNotFoundError(
                errcode="L3207",
                message=f"Query item not found.\n\t[RESOURCE] {resource}\n\t[QUERY   ] {query}"
            )

        return item

    @classmethod
    def commit(cls):
        if cls.__filepath__ is None:
            return

        with open(cls.__filepath__, 'wb') as f:
            pickle.dump(cls._MEMORY_STORE, f)

    @classmethod
    def load_memory(cls):
        if cls.__filepath__ is None:
            return {}

        if not os.path.isfile(cls.__filepath__):
            return {}

        with open(cls.__filepath__, 'rb') as f:
            data = pickle.load(f)
            if not isinstance(data, dict):
                logger.warning('Invalid memory store data [%s]: %s', cls.__filepath__, data)
                return {}

            return data

    @classmethod
    def connect(cls, *args, **kwargs):
        if not hasattr(cls, '_MEMORY_STORE'):
            cls._MEMORY_STORE = cls.load_memory()

        return cls._MEMORY_STORE

    async def update(self, resource, query, **changes):
        store = self._get_memory(resource)
        for item in await self.find(resource, query):
            store[item._id] = item.set(**changes)

    update_one = update

    async def insert(self, resource, record):
        store = self._get_memory(resource)

        if record._id in store:
            raise ValueError('Item already exists.')

        store[record._id] = record
        return record

    async def invalidate_one(self, resource, *args, **kwargs):
        pass

    @classmethod
    async def native_query(cls, query, *params, **options):
        return query

    def defaults(self):
        return {"_etag": identifier.UUID_GENR_BASE64()}
