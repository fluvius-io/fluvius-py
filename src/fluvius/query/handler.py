import re
from typing import Optional, List, Dict, Any
from fluvius.data import BackendQuery, nullable, DataModel
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

RX_SELECT_SPLIT = re.compile(r"[,;\s]+")
RX_TEXT_SPLIT = re.compile(r"[,]+")


def validate_query_schema(schema_cls):
    if issubclass(schema_cls, QuerySchema):
        return schema_cls

    raise ValueError(f'Invalid query model: {schema_cls}')


class QueryHandler(object):
    _registry  = {}
    __prefix__ = None

    def __init_subclass__(cls):
        cls._registry = {}
        cls.__prefix__ = cls.__dict__.get('__prefix__') or cls.__name__

    @classmethod
    def register_model(cls, query_identifier):
        def _decorator(model_cls):
            if query_identifier in cls._registry:
                raise ValueError(f'Resource identifier is already registered: {query_identifier} => {model_cls}')

            cls._registry[query_identifier] = validate_query_schema(model_cls)(query_identifier=query_identifier)
            return model_cls

        return _decorator

    async def query(self, query_identifier, frontend_query=None, **kwargs):
        query_schema = self._registry[query_identifier]
        fe_query = query_schema.validate_frontend_query(frontend_query, **kwargs)
        backend_query = self.construct_backend_query(query_schema, fe_query)

        backend_query = await self.check_backend_query(query_schema, backend_query)
        results, meta = await self.run_backend_query(query_schema, backend_query)

        return self.process_result(results, meta)

    def construct_backend_query(self, query_schema, fe_query):
        """ Convert from the frontend query to the backend query """

        query_scope = query_schema.base_query(fe_query)
        return BackendQuery.create(
            identifier=fe_query.identifier,
            scope=query_scope,
            where=fe_query.stmt,
            limit=fe_query.limit,
            offset=fe_query.offset,
            select=fe_query.select,
            sort=fe_query.sort
        )

    async def run_backend_query(self, query_schema, backend_query: BackendQuery):
        """ Execute the backend query with the state manager and return """
        return backend_query, None

    async def check_backend_query(self, query_schema, backend_query):
        return backend_query

    def process_result(self, results, metadata):
        return results, metadata


class DomainQueryHandler(QueryHandler):
    def __init__(self, app=None):
        self._app = app
        self._manager = self.__data_manager__(app)

    @property
    def manager(self):
        return self._manager

    async def run_backend_query(self, query_schema, backend_query: BackendQuery):
        """ Execute the backend query with the state manager and return """
        result = await self.manager.find_all(query_schema.meta.backend_resource, backend_query)
        return list(result), None

    async def check_backend_query(self, query_schema, backend_query):
        return backend_query
