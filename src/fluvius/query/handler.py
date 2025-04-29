import re
from typing import Optional, List, Dict, Any
from fluvius.data import BackendQuery, DataModel
from fluvius.helper import camel_to_lower
from .schema import QuerySchema, FrontendQuery, FrontendQueryParams
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

RX_SELECT_SPLIT = re.compile(r"[,;\s]+")
RX_TEXT_SPLIT = re.compile(r"[,]+")


def validate_query_schema(schema_cls):
    if issubclass(schema_cls, QuerySchema):
        return schema_cls

    raise ValueError(f'Invalid query model: {schema_cls}')


class QueryManagerMeta(DataModel):
    prefix: str
    tags: List[str]
    name: str
    desc: str

class QueryManager(object):
    _registry  = {}
    __prefix__ = None

    class Meta:
        pass

    def __init_subclass__(cls):
        cls._registry = {}
        cls.Meta = QueryManagerMeta.create(cls.Meta, defaults={
            'name': cls.__name__,
            'prefix': camel_to_lower(cls.__prefix__ or cls.__name__),
            'desc': (cls.__doc__ or '').strip(),
            'tags': [cls.__name__,]
        })

    @classmethod
    def register_schema(cls, schema_cls):
        query_identifier = schema_cls.Meta.query_identifier
        if query_identifier in cls._registry:
            raise ValueError(f'Resource identifier is already registered: {query_identifier} => {schema_cls}')

        cls._registry[query_identifier] = validate_query_schema(schema_cls)()
        return schema_cls

    async def query(self, query_identifier, query_params: Optional[FrontendQueryParams]=None, **kwargs):
        query_schema = self._registry[query_identifier]
        query_params = query_params or FrontendQueryParams()
        fe_query = query_params.build_query(query_schema)
        backend_query = self.construct_backend_query(query_schema, fe_query, **kwargs)
        backend_query = await self.validate_backend_query(query_schema, backend_query)
        data, meta = await self.execute_query(query_schema, backend_query)

        return self.process_result(data, meta)

    def construct_backend_query(self, query_schema, fe_query, **kwargs):
        """ Convert from the frontend query to the backend query """

        composite_scope = query_schema.base_query(fe_query)
        return BackendQuery.create(
            identifier=fe_query.identifier,
            scope=composite_scope,
            where=fe_query.query,
            limit=fe_query.limit,
            offset=fe_query.offset,
            select=fe_query.select,
            sort=fe_query.sort
        )

    async def execute_query(self, query_schema, backend_query: BackendQuery):
        """ Execute the backend query with the state manager and return """
        raise NotImplementedError('QuerySchema.execute_query')

    async def validate_backend_query(self, query_schema, backend_query):
        return backend_query

    def process_result(self, data, meta):
        return data, meta


class DomainQueryManager(QueryManager):
    def __init__(self, app=None):
        self._app = app
        self._manager = self.__data_manager__(app)

    @property
    def manager(self):
        return self._manager

    async def execute_query(self, query_schema, backend_query: BackendQuery):
        """ Execute the backend query with the state manager and return """
        result = await self.manager.find_all(query_schema.Meta.backend_resource, backend_query)
        return list(result), None
