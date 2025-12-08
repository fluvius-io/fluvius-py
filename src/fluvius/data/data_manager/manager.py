""" Data Access Interface

    @TODO: Add transaction management primitives
"""

from collections.abc import Mapping
from contextlib import asynccontextmanager
from datetime import datetime
from functools import wraps, partial
from types import SimpleNamespace
from typing import List, Optional, Type, Union

from fluvius.helper import select_value, ImmutableNamespace
from fluvius.data import UUID_TYPE, UUID_GENR, logger, timestamp, config
from fluvius.data.helper import serialize_mapping, generate_etag
from fluvius.data.data_driver import DataDriver
from fluvius.data.data_model import DataModel, BlankModel
from fluvius.data.query import BackendQuery
from fluvius.data.exceptions import ItemNotFoundError
from fluvius.error import BadRequestError, InternalServerError

from fluvius.data.constant import (
    INTRA_DOMAIN_ITEM_ID_FIELD, 
    INTRA_DOMAIN_SCOPE_FIELD, 
    ETAG_FIELD,
    MODEL_RESOURCE_ATTRIB
)

DEBUG = config.DEBUG
ATTR_QUERY_MARKER = '__domain_query__'
BACKEND_QUERY_LIMIT = config.BACKEND_QUERY_INTERNAL_LIMIT
RAISE_NESTED_TRANSACTION_ERROR = False

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

    if callable(key_or_func):
        return _decorator(key_or_func)

    return _decorator

list_query = partial(data_query, unwrapper=list_unwrapper)
item_query = partial(data_query, unwrapper=item_unwrapper)
value_query = partial(data_query, unwrapper=scalar_unwrapper)

class ResourceAlreadyRegistered(Exception):
    pass


class DataAccessManagerBase(object):
    # Instance of database driver that provides data to the manager
    __connector__ = None
    __automodel__ = None
    __config__    = ImmutableNamespace

    """ Domain data access manager """
    def __init_subclass__(cls, connector=None, automodel=None):
        super().__init_subclass__()  # See: NOTES.md @ Init subclass

        if cls.__dict__.get('__abstract__'):
            return

        cls._MODELS = {}
        cls._RESOURCES =  {}
        cls._AUTO = {}
        cls._QUERIES = tuple(
            name for name, method in cls.__dict__.items()
            if hasattr(method, ATTR_QUERY_MARKER)
        )

        cls.__connector__ = select_value(connector, cls.__connector__)
        cls.__automodel__ = select_value(automodel, cls.__automodel__, default=True)
        cls.setup_model()

    def __init__(self, domain=None, app=None, **config):
        self._transaction = None
        self._proxy = ReadonlyDataManagerProxy(self)
        self._connector = self.setup_connector(config)
        self._app = app
        self._domain = domain
        self._config = self.validate_config(config)

    def validate_config(self, config, **defaults):
        config = defaults | config
        return self.__config__(**{k.upper(): v for k, v in config.items()})

    @property
    def app(self):
        return self._app

    @property
    def config(self):
        return self._config

    @property
    def domain(self):
        return self._domain

    @classmethod
    def setup_model(cls):
        if not cls.__automodel__:
            return

        for model_name, data_schema in cls.__connector__.__data_schema_registry__.items():
            model = cls.generate_model(data_schema)

            try:
                cls.register_model(model_name)(model, is_generated=True)
            except ResourceAlreadyRegistered:
                logger.warning(f'[W12.931] Model already registered: {model_name}')


    @classmethod
    def generate_model(cls, data_schema):
        if not isinstance(cls.__automodel__, bool):
            raise InternalServerError('E00.201', f'__automodel__ only accept True / False: {cls.__automodel__}')

        return data_schema
        # return type(f"{data_schema.__name__}DAModel", (BlankModel, ), {})

    @classmethod
    def register_model(cls, model_name: str):
        def _decorator(model_cls: Type[DataModel], is_generated: bool=False):
            # if not issubclass(model_cls, DataModel):
            #     logger.warning(f'Data model is not a subclass of DataModel: {model_cls}')

            if model_cls in cls._RESOURCES:
                raise ResourceAlreadyRegistered(f'Model already registered: {model_cls} => {cls._RESOURCES[model_cls]}')

            if model_name in cls._MODELS and not cls._AUTO.get(model_name):
                raise ResourceAlreadyRegistered(f'Resource already registered: {model_name} => {cls._MODELS[model_name]}')

            cls._RESOURCES[model_cls] = model_name
            cls._MODELS[model_name] = model_cls
            cls._AUTO[model_name] = is_generated

            DEBUG and logger.debug(f'{"Generated" if is_generated else "Registered"} model: {model_name} => {model_cls}')
            return model_cls

        return _decorator

    @classmethod
    def lookup_model(cls, model_name):
        return cls._MODELS[model_name]

    @classmethod
    def lookup_record_model(cls, record):
        model_cls = record.__class__
        return cls._RESOURCES[model_cls]

    def validate_config(self, config):
        if isinstance(config, self.__config__):
            return config

        return self.__config__(**config)

    @property
    def connector(self):
        return self._connector

    def connect(self, *args, **kwargs):
        return self.connector.connect(*args, **kwargs)

    async def disconnect(self):
        await self.connector.disconnect()
        return self

    @asynccontextmanager
    async def transaction(self, *args):
        if self._transaction is not None:
            if RAISE_NESTED_TRANSACTION_ERROR:
                raise InternalServerError('E00.202', f'Nested transaction detected in {self.__class__.__name__}')

        async with self.connector.transaction(*args) as transaction:
            self._transaction = transaction
            yield self._proxy
            self._transaction = None

    async def flush(self):
        await self.connector.flush()
        return self

    @property
    def context(self):
        if self._context is None:
            raise InternalServerError('E00.203', 'State Manager context is not initialized.')

        return self._context

    def setup_connector(self, config):
        con_cls = self.__connector__
        if not con_cls or not issubclass(con_cls, DataDriver):
            raise InternalServerError('E00.204', f'Invalid data driver/connector: {con_cls}')

        return con_cls(**config)

    @classmethod
    def create(cls, model_name: str, data: dict = None, / , **kwargs) -> DataModel:
        """ Create a single resource instance in memory (not saved yet!) """

        defvals = cls.defaults(model_name, data)
        defvals.update(**kwargs)
        return cls._wrap_item(model_name, defvals)

    @classmethod
    def defaults(cls, model_name: str, data=None) -> dict:
        defvals = data or {}
        ts = timestamp()
        defvals.update(_created=ts, _updated=ts)
        return defvals

    @classmethod
    def _serialize(cls, model_name, item):
        model = cls.lookup_model(model_name)
        if not isinstance(item, model):
            raise InternalServerError('E00.206', f'Cannot serialize item. It must be an instance of [{model}].')

        return model.serialize(item)

    @classmethod
    def _wrap_item(cls, model_name, data):
        model_cls = cls.lookup_model(model_name)
        if isinstance(data, model_cls):
            return data

        return model_cls(**data)

    @classmethod
    def _wrap_model(cls, model_cls, data):
        if isinstance(data, model_cls):
            return data
        
        if not isinstance(data, Mapping):
            data = serialize_mapping(data)

        return model_cls(**data)

    @classmethod
    def _wrap_many(cls, model_name, *items):
        return cls._wrap_list(model_name, items)

    @classmethod
    def _wrap_list(cls, model_name, item_list):
        model_cls = cls.lookup_model(model_name)
        return [cls._wrap_model(model_cls, data) for data in item_list]

    async def native_query(self, query, *params, unwrapper=list_unwrapper, **query_options):
        return await self.connector.native_query(query, *params, unwrapper=unwrapper, **query_options)

    def dump_log(cls):
        logger.info('cls._RESOURCES = %s', str(cls._RESOURCES))
        logger.info('cls._MODEL = %s', str(cls._RESOURCES))


class DataFeedManager(DataAccessManagerBase):
    """
    Thin wrapper around data feed class that allow access to models (multiple) registered with that data feed.
    """
    __abstract__ = True

    async def insert(self, record: DataModel):
        model_cls = self.lookup_record_model(record)
        data = self._serialize(model_cls, record)
        result = await self.connector.insert(model_cls, data)
        return result

    async def insert_data(self, model_name, data):
        return await self.connector.insert(model_name, data)

    async def update_data(self, model_name, identifier, **data):
        query = BackendQuery(identifier=identifier)
        record = await self.connector.find_one(model_name, query)
        record = await self.connector.update_record(record, **data)
        await self.flush()
        return record

    async def update(self, record: DataModel, updates: dict):
        model_cls = self.lookup_record_model(record)
        query = BackendQuery(identifier=record._id)
        return await self.connector.update_record(model_cls, record, **updates)


class DataAccessManager(DataAccessManagerBase):
    """
    General data access manager. A data access manager abstract map each schema (i.e. database driver's data model)
    to application data model which is database agnostic, that way application code can be used across
    all database backend.
    """

    __abstract__ = True

    async def fetch(self, model_name: str, identifier: UUID_TYPE , etag: str=None, /, **kwargs) -> DataModel:
        """ Fetch exactly 1 items from the data store using its primary identifier """
        q = BackendQuery.create(identifier=identifier, etag=etag, where=kwargs)
        item = await self.connector.find_one(model_name, q)
        return self._wrap_item(model_name, item)

    async def fetch_with_domain_sid(self, model_name: str, identifier, domain_sid, etag=None, / , **kwargs) -> DataModel:
        """ Fetch exactly 1 items from the data store using its intra domain identifier """
        scope = {INTRA_DOMAIN_SCOPE_FIELD: domain_sid}
        q = BackendQuery.create(identifier=identifier, scope=scope, where=kwargs, etag=etag)
        data = await self.connector.find_one(model_name, q)
        return self._wrap_item(model_name, data)

    async def find_one(self, model_name: str, q=None, /, **query) -> DataModel:
        """ Fetch exactly 1 item from the data store using either a query object or where statements
            Raises an error if there are 0 or multiple results """
        q = BackendQuery.create(q, **query, limit=1, offset=0)
        if q.limit != 1 or q.offset != 0:
            raise BadRequestError('E00.205', f'Invalid find_one query: {q}')

        try:
            item = await self.connector.find_one(model_name, q)
            return self._wrap_item(model_name, item)
        except ItemNotFoundError:
            return None

    async def find_all(self, model_name: str, q=None, return_meta=None, **query) -> List[DataModel]:
        """ Find all matching items, always starts with offset = 0 and retrieve all items """
        q = BackendQuery.create(q, **query, offset=0, limit=BACKEND_QUERY_LIMIT)
        data = await self.connector.query(model_name, q, return_meta)
        return self._wrap_list(model_name, data)

    async def query(self, model_name: str, q=None, return_meta=None, **query) -> List[DataModel]:
        """ Query with offset and limits """
        q = BackendQuery.create(q, **query)
        data = await self.connector.query(model_name, q, return_meta)
        return self._wrap_list(model_name, data)
    
    async def connector_query(self, model_name: str, q=None, return_meta=None, **query):
        """ Query with offset and limits """
        q = BackendQuery.create(q, **query)
        return await self.connector.query(model_name, q, return_meta)

    async def invalidate(self, record: DataModel):
        model_name = self.lookup_record_model(record)
        query   = BackendQuery.create(identifier=record._id, etag=record._etag)
        etag    = generate_etag(record)
        ts      = timestamp()
        changes = dict(_deleted=ts, _updated=ts, _etag=etag)
        return await self.connector.update_data(model_name, query, **changes)

    async def update(self, record: DataModel, /, **updates):
        model_name = self.lookup_record_model(record)
        q    = BackendQuery.create(identifier=record._id, etag=record._etag)
        etag = generate_etag(record)
        ts   = timestamp()
        changes = updates | dict(_updated=ts, _etag=etag)
        return await self.connector.update_data(model_name, q, **changes)

    async def remove(self, record: DataModel):
        model_name = self.lookup_record_model(record)
        query = BackendQuery.create(identifier=record._id, etag=record._etag)
        return await self.connector.remove_one(model_name, query)

    async def insert(self, record: DataModel):
        model_name = self.lookup_record_model(record)
        data = self._serialize(model_name, record)
        result = await self.connector.insert(model_name, data)
        return result

    async def upsert(self, model_name, record: DataModel):
        data = self._serialize(model_name, record)
        updt = timestamp()
        # data['_updated'] = updt
        # data['_etag'] = generate_etag(data)
        return await self.connector.upsert(model_name, data)
    
    async def insert_data(self, model_name: str, *records: list[dict]):
        updt = timestamp()
        for data in records:
            data['_updated'] = updt
            data['_etag'] = generate_etag(data)
            await self.connector.insert(model_name, data)

    async def upsert_data(self, model_name: str, *records: list[dict]):
        updt = timestamp()
        for data in records:
            data['_updated'] = updt
            data['_etag'] = generate_etag(data)
            await self.connector.upsert(model_name, data)

    async def invalidate_data(self, model_name: str, identifier: UUID_TYPE, etag=None, /, **updates):
        q = BackendQuery.create(identifier=identifier, etag=etag)
        updt = timestamp()
        etag = generate_etag(updates)
        return await self.connector.update_data(model_name, q, _updated=updt, _deleted=updt, _etag=etag, **updates)

    async def update_data(self, model_name: str, identifier: UUID_TYPE, etag=None, /, **updates):
        query = BackendQuery.create(identifier=identifier, etag=etag)
        updt = timestamp()
        etag = generate_etag(updates)
        return await self.connector.update_data(model_name, query, _updated=updt, _etag=etag, **updates)

class ReadonlyDataManagerProxy(object):
    def __init__(self, data_manager):
        self.create = getattr(data_manager, 'create', None)
        self.fetch = getattr(data_manager, 'fetch', None)
        self.fetch_with_domain_sid = getattr(data_manager, 'fetch_with_domain_sid', None)
        self.find_all = getattr(data_manager, 'find_all', None)
        self.find_one = getattr(data_manager, 'find_one', None)

        for query_name in data_manager._QUERIES:
            query_method = getattr(data_manager, query_name)
            setattr(self, query_name, query_method)

