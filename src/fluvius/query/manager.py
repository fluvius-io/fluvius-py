import re
import sqlalchemy

from typing import Optional, List, Dict, Any
from fluvius.data import BackendQuery, DataModel
from fluvius.helper import camel_to_lower
from fluvius.error import InternalServerError
from .schema import QuerySchema, FrontendQuery
from . import config

DESELECT = "deselect"
LIMIT = "max_results"
OFFSET = "offset"
PAGE = "page"
QUERY = "where"
SELECT = "select"
SELECT_ESCAPE_CHAR = "_"
SHOW_DELETED = "show_deleted"
SORT = "sort"
TEXT = "txt"

LIMIT_DEFAULT = config.DEFAULT_QUERY_LIMIT
ALLOW_ESCAPE = config.ALLOW_SELECT_ESCAPE
DEVELOPER_MODE = config.DEVELOPER_MODE

RX_SELECT_SPLIT = re.compile(r"[,;\s]+")
RX_TEXT_SPLIT = re.compile(r"[,]+")


def _compute_select(fe_query, query_schema):
    if query_schema.Meta.select_all:
        return fe_query.select

    if not fe_query.select:
        return query_schema.select_fields

    return query_schema.select_fields & set(fe_query.select)

class QueryManagerMeta(DataModel):
    name: str
    api_prefix: str
    api_tags: Optional[List[str]] = None
    api_docs: Optional[str] = None


class QueryManager(object):
    _registry  = {}

    class Meta:
        pass

    def __init_subclass__(cls):
        if cls.__dict__.get('__abstract__'):
            return

        cls._registry = {}
        cls.Meta = QueryManagerMeta.create(cls.Meta, defaults={
            'name': cls.__name__,
            'api_prefix': camel_to_lower(cls.__name__),
            'api_docs': (cls.__doc__ or '').strip(),
            'api_tags': [cls.__name__,]
        })

    @classmethod
    def validate_query_schema(cls, schema_cls):
        if issubclass(schema_cls, QuerySchema):
            return schema_cls

        raise ValueError(f'Invalid query model: {schema_cls}')

    @classmethod
    def register_schema(cls, query_identifier):
        def _decorator(schema_cls):
            if getattr(schema_cls, '_identifier', None):
                raise ValueError(f'QuerySchema already registered with identifier: {schema_cls._identifier}')

            schema_cls._identifier = query_identifier
            if query_identifier in cls._registry:
                raise ValueError(f'Resource identifier is already registered: {query_identifier} => {schema_cls}')

            query_schema = cls.validate_query_schema(schema_cls)
            cls._registry[query_identifier] = query_schema()
            return query_schema

        return _decorator

    @classmethod
    def lookup_query_schema(cls, identifier):
        return cls._registry[identifier]

    def validate_fe_query(self, query_schema, fe_query, kwargs):
        if fe_query is None:
            return FrontendQuery(**kwargs)

        if kwargs:
            return fe_query.set(**kwargs)

        return fe_query

    async def query(self, query_identifier, fe_query: Optional[FrontendQuery]=None, **kwargs):
        query_schema = self.lookup_query_schema(query_identifier)

        fe_query = self.validate_fe_query(query_schema, fe_query, kwargs)
        be_query = self.construct_backend_query(query_schema, fe_query)
        data, meta = await self.execute_query(query_schema, be_query, {})

        return self.process_result(data, meta)

    async def query_item(self, query_identifier, item_identifier, fe_query: Optional[FrontendQuery]=None, **kwargs):
        query_schema = self.lookup_query_schema(query_identifier)
        fe_query = self.validate_fe_query(query_schema, fe_query, kwargs)
        be_query = self.construct_backend_query(query_schema, fe_query, identifier=item_identifier)
        data, meta = await self.execute_query(query_schema, be_query, None)

        result, _ = self.process_result(data, meta)
        return result[0]


    def construct_backend_query(self, query_schema, fe_query, identifier=None, scope=None):
        """ Convert from the frontend query to the backend query """
        scope   = query_schema.base_query(scope)
        query   = query_schema.validate_schema_args(fe_query)
        limit   = fe_query.size
        offset  = (fe_query.page - 1) * fe_query.size
        select  = _compute_select(fe_query, query_schema)

        backend_query = BackendQuery.create(
            identifier=identifier,
            limit=limit,
            offset=offset,
            scope=scope,
            select=select,
            sort=fe_query.sort,
            where=query,
            mapping=query_schema.query_mapping
        )
        return self.validate_backend_query(query_schema, backend_query)

    async def execute_query(self, query_schema, backend_query: BackendQuery, meta: Optional[Dict] = None):
        """ Execute the backend query with the state manager and return """
        raise NotImplementedError('QuerySchema.execute_query')

    def validate_backend_query(self, query_schema, backend_query):
        return backend_query

    def process_result(self, data, meta):
        return data, meta


class DomainQueryManager(QueryManager):
    __abstract__ = True

    def __init__(self, app=None):
        self._app = app
        self._data_manager = self.__data_manager__(app)

    @property
    def data_manager(self):
        return self._data_manager

    async def execute_query(self, query_schema, backend_query: BackendQuery, meta: Optional[Dict] = None):
        """ Execute the backend query with the state manager and return """
        resource = query_schema.backend_resource()
        try:
            data = await self.data_manager.query(resource, backend_query, return_meta=meta)
        except sqlalchemy.exc.ProgrammingError as e:
            details = None if not DEVELOPER_MODE else {
                "pgcode": e.orig.pgcode,
                "statement": e.statement,
                "params": e.params,
            }

            raise InternalServerError("Q101-501", f"Query Error [{e.orig.pgcode}]: {e.orig}", details)

        return data, meta
