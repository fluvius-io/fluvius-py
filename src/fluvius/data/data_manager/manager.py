""" Data Access Interface

    @TODO: Add transaction management primitives
"""

from functools import wraps, partial
from types import SimpleNamespace
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional, Type, Union

from fluvius.data import UUID_TYPE, UUID_GENR, logger, timestamp, config
from fluvius.data.data_driver import DataDriver
from fluvius.data.data_model import DataModel, BlankModel
from fluvius.data.query import BackendQuery
from fluvius.data.exceptions import ItemNotFoundError

from fluvius.data.constant import (
    INTRA_DOMAIN_ITEM_ID_FIELD, 
    INTRA_DOMAIN_SCOPE_FIELD, 
    ETAG_FIELD,
    MODEL_RESOURCE_ATTRIB
)

DEBUG = config.DEBUG
ATTR_QUERY_MARKER = '__domain_query__'


def list_unwrapper(cursor):
    return tuple(SimpleNamespace(**row._asdict()) for row in cursor.all())


def item_unwrapper(cursor):
    return SimpleNamespace(**cursor.one()._asdict())


def scalar_unwrapper(cursor):
    return cursor.scalar_one()


def data_query(key_or_func=None, **query_options):
    """ Extensible methods:
        - unwrapper: unpack the results into data
        - query_runner: execute the results with underlying data

    """
    def _decorator(func):
        setattr(func, ATTR_QUERY_MARKER, func.__name__)

        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            query = func(self, *args, **kwargs)
            if isinstance(query, tuple):
                query, *params = query
            else:
                params = tuple()

            return await self.native_query(query, *params, **query_options)

        return wrapper

        raise ValueError(f'Invalid query result type: {result} (available: list, item, value)')

    if callable(key_or_func):
        return _decorator(key_or_func)

    return _decorator

list_query = partial(data_query, unwrapper=list_unwrapper)
item_query = partial(data_query, unwrapper=item_unwrapper)
value_query = partial(data_query, unwrapper=scalar_unwrapper)

class ResourceAlreadyRegistered(Exception):
    pass


class DataAccessManagerBase(object):
    __config__ = SimpleNamespace
    __connector__ = None
    __auto_model__ = False

    """ Domain data access manager """
    def __init_subclass__(cls):
        cls._MODELS = {}
        cls._RESOURCES =  {}
        cls._AUTO = {}
        cls._QUERIES = tuple(
            name for name, method in cls.__dict__.items()
            if hasattr(method, ATTR_QUERY_MARKER)
        )

    def __init__(self, **config):
        self._config = self.validate_config(config)
        self._proxy = ReadonlyDataManagerProxy(self)
        self.setup_connector(**config)
        self.setup_model()

    def setup_model(self):
        if not self.__auto_model__:
            return

        for resource_name, schema_model in self.connector._schema_model.items():
            model = self._gen_model(schema_model)
            try:
                self.register_model(resource_name, auto_model=True)(model)
            except ResourceAlreadyRegistered:
                logger.warning(f'Model already registered: {resource_name}')


    def _gen_model(self, schema_model):
        if self.__auto_model__ == 'schema':
            return schema_model

        return type(f"{schema_model.__name__}_Model", (BlankModel, ), {})

    @classmethod
    def register_model(cls, resource: str, auto_model: bool=False):
        def _decorator(model_cls: DataModel):
            # if not issubclass(model_cls, DataModel):
            #     logger.warning(f'Data model is not a subclass of DataModel: {model_cls}')

            if model_cls in cls._RESOURCES:
                raise ResourceAlreadyRegistered(f'Model already registered: {model_cls} => {cls._RESOURCES[model_cls]}')

            if resource in cls._MODELS and not cls._AUTO.get(resource):
                raise ResourceAlreadyRegistered(f'Resource already registered: {resource} => {cls._MODELS[resource]}')

            cls._RESOURCES[model_cls] = resource
            cls._MODELS[resource] = model_cls
            cls._AUTO[resource] = auto_model

            logger.info(f'Register {"auto-generated" if auto_model else ""} model: {resource} => {model_cls}')
            return model_cls

        return _decorator

    @classmethod
    def lookup_model(cls, resource):
        return cls._MODELS[resource]

    @classmethod
    def lookup_resource(cls, record):
        model_cls = record.__class__
        return cls._RESOURCES[model_cls]

    @classmethod
    def _wrap(cls, resource, item):
        model = cls.lookup_model(resource)
        if isinstance(item, model):
            return item

        return model(**item)

    @classmethod
    def _wrap_list(cls, resource, item_list):
        return [self._wrap_model(resource, item) for item in item_list]

    @classmethod
    def _serialize(cls, resource, item):
        model = cls.lookup_model(resource)
        return model.serialize(item)

    def validate_config(self, config):
        if isinstance(config, self.__config__):
            return config

        return self.__config__(**config)

    def connect(self, *args, **kwargs):
        self.connector.connect(*args, **kwargs)
        return self

    def disconnect(self):
        self.connector.disconnect()
        return self

    @asynccontextmanager
    async def transaction(self, *args, **kwargs):
        async with self.connector.transaction(*args, **kwargs) as transaction:
            self._transaction = transaction
            yield self._proxy
            self._transaction = None

    async def flush(self):
        await self.connector.flush()
        return self

    @property
    def context(self):
        if self._context is None:
            raise RuntimeError('State Manager context is not initialized.')

        return self._context

    @property
    def connector(self):
        return self._connector

    def setup_connector(self, **config):
        con_cls = self.__connector__
        if not con_cls or not issubclass(con_cls, DataDriver):
            raise ValueError(f'Invalid data driver/connector: {con_cls}')

        self._connector = con_cls(**config)

    @classmethod
    def create(cls, resource: str, data: dict = None, / , **kwargs) -> DataModel:
        """ Create a single resource instance in memory (not saved yet!) """

        defvals = cls.defaults(resource, data)
        return cls._wrap_model(resource, dict(**defvals, **kwargs))

    @classmethod
    def defaults(cls, resource: str, data=None) -> dict:
        defvals = data or {}
        defvals.update(_created=timestamp(), _updated=timestamp())
        return defvals

    @classmethod
    def _wrap_model(cls, resource, data):
        model_cls = cls.lookup_model(resource)
        if isinstance(data, model_cls):
            return data

        return model_cls(**data)

    @classmethod
    def _wrap_model_list(cls, resource, item_list):
        return [cls._wrap_model(resource, data) for data in item_list]

    async def query(self, query, *params, unwrapper=list_unwrapper, **query_options):
        return await self.connector.query(query, *params, unwrapper=unwrapper, **query_options)

    def dump_log(cls):
        logger.info('cls._RESOURCES = %s', str(cls._RESOURCES))
        logger.info('cls._MODEL = %s', str(cls._RESOURCES))


class DataFeedManager(DataAccessManagerBase):
    """ Thin wrapper around data feed class that allow access to resources (multiple) registered with that data feed.
    """
    def __init_subclass__(cls):
        super().__init_subclass__()

    async def insert(self, record: DataModel):
        resource = self.lookup_resource(record)
        data = self._serialize(resource, record)
        result = await self.connector.insert(resource, data)
        return result

    async def insert_data(self, resource, data):
        return await self.connector.insert(resource, data)

    async def update_data(self, resource, identifier, **data):
        record = await self.connector.find_one(resource, identifier=identifier)
        record = await self.connector.update_record(record, **data)
        await self.flush()
        return record

    async def update(self, record: DataModel, updates: dict):
        resource = self.lookup_resource(record)
        return await self.connector.update_record(resource, record, **updates)


class DataAccessManager(DataAccessManagerBase):
    """ Domain data access manager """

    def __init_subclass__(cls):
        super().__init_subclass__()

    async def fetch(self, resource: str, identifier: UUID_TYPE, / , etag=None, where=None) -> DataModel:
        """ Fetch exactly 1 items from the data store using its primary identifier """
        scope = {ETAG_FIELD: etag} if etag else None
        q = BackendQuery.create(identifier=identifier, limit=1, scope=scope, where=where)
        item = await self.connector.find_one(resource, q)
        return self._wrap_model(resource, item)

    async def fetch_by_intra_id(self, resource: str, intra_id, domain_id, / , etag=None, where=None) -> DataModel:
        """ Fetch exactly 1 items from the data store using its intra domain identifier """
        scope = {INTRA_DOMAIN_SCOPE_FIELD: domain_id, INTRA_DOMAIN_ITEM_ID: intra_id}
        if etag:
            scope[ETAG_FIELD] = etag

        q = BackendQuery.create(scope=scope, where=where, limit=1)
        data = await self.connector.find_one(resource, q)
        return self._wrap_model(resource, data)

    async def find_one(self, resource: str, q=None, **query) -> DataModel:
        """ Fetch exactly 1 item from the data store using either a query object or where statements
            Raises an error if there are 0 or multiple results """
        q = BackendQuery.create(q, **query, limit=1)

        try:
            item = await self.connector.find_one(resource, q)
            return self._wrap_model(resource, item)
        except ItemNotFoundError:
            return None

    async def find_all(self, resource: str, q=None, **query) -> List[DataModel]:
        """ Fetch multiple items from the data store using either a query object or where statements
            Each entry will be wrapped using corresponding DataModel """
        q = BackendQuery.create(query)
        data = await self.connector.find_all(resource, q)
        return self._wrap_model_list(resource, data)

    async def invalidate(self, record: DataModel, updates=None):
        resource = self.lookup_resource(record)
        return await self.connector.invalidate_record(resource, record, updates)

    async def invalidate_one(self, resource: str, identifier: UUID_TYPE, updates=None, *, etag=None, where=None):
        scope = {ETAG_FIELD: etag} if etag else None
        q = BackendQuery.create(identifier=identifier, scope=scope, where=where)
        updates = updates or {}
        updates['_deleted'] = timestamp()
        return await self.connector.update(resource, q, updates)

    async def invalidate_many(self, resource: str, updates=None, q=None, **query):
        q = BackendQuery.create(query)
        return await self.connector.invalidate_many(resource, q, updates)

    async def update(self, record: DataModel, updates: dict):
        resource = self.lookup_resource(record)
        return await self.connector.update_record(resource, record, **updates)

    async def update_one(self, resource: str, identifier: UUID_TYPE, updates=None, *, etag=None, where=None):
        scope = {ETAG_FIELD: etag} if etag else None
        q = BackendQuery.create(identifier=identifier, scope=scope, where=where)
        return await self.connector.update(resource, q, updates)

    async def update_many(self, resource: str, updates: dict, q=None, **query):
        q = BackendQuery.create(query)
        return await self.connector.update_many(resource, q, updates)

    async def remove(self, record):
        resource = self.lookup_resource(record)
        return await self.connector.remove_record(resource, record)

    async def remove_many(self, resource: str, q=None, **query):
        q = BackendQuery.create(q, **query)
        return await self.connector.remove_data(resource, q)

    async def insert(self, record: DataModel):
        resource = self.lookup_resource(record)
        data = self._serialize(resource, record)
        result = await self.connector.insert(resource, data)
        return result

    async def insert_data(self, resource, data):
        result = await self.connector.insert(resource, data)
        return result

    async def insert_many(self, resource: str, *records: list[DataModel]):
        data = [self._serialize(resource, rec) for rec in records]
        return await self.connector.insert(resource, *data)

    async def upsert(self, record: DataModel):
        resource = self.lookup_resource(record)
        return await self.connector.upsert(resource, values)

    async def upsert_many(self, resource, *records):
        result = []
        for record in records:
            result.append(await self.connector.upsert_record(resource, record))
        return result

    async def native_query(self, *args, **kwargs):
        return await self.connector.native_query(*args, **kwargs)


class ReadonlyDataManagerProxy(object):
    def __init__(self, statemgr):
        self.create = getattr(statemgr, 'create', None)
        self.fetch = getattr(statemgr, 'fetch', None)
        self.fetch_by_intra_id = getattr(statemgr, 'fetch_by_intra_id', None)
        self.find_all = getattr(statemgr, 'find_all', None)
        self.find_one = getattr(statemgr, 'find_one', None)

        for query_name in statemgr._QUERIES:
            query_method = getattr(statemgr, query_name)
            setattr(self, query_name, query_method)

