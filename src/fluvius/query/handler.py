import re
from typing import Optional
from fluvius.data import BackendQuery, nullable, DataModel
from .schema import QuerySchema
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


class ParsedParams(DataModel):
    identifier: Optional[str] = None

    limit: int = config.DEFAULT_QUERY_LIMIT
    offset: int = 0
    page: int = 1

    select: Optional[List[str]] = None
    deselect = Optional[List[str]] = None

    sort = Optional[List[str]] = None
    args = Optional[Dict[str, str]] = None
    opts = Optional[Dict[str, str]] = None



def validate_query_model(model):
    if issubclass(model, QuerySchema):
        return model

    raise ValueError(f'Invalid query model: {model}')


class QueryHandler(object):
    _registry = {}

    def __init_subclass__(cls):
        cls._registry = {}

    @classmethod
    def register_model(cls, query_identifier):
        def _decorator(model_cls):
            if query_identifier in cls._registry:
                raise ValueError(f'Resource identifier is already registered: {query_identifier} => {model_cls}')

            cls._registry[query_identifier] = validate_query_model(model_cls)(query_identifier=query_identifier)
            return model_cls

        return _decorator

    async def query(self, query_identifier, parsed_params):
        query_schema = self._registry[query_identifier]
        query_params = query_schema.validate_query(parsed_params)
        backend_query = self.construct_query(query_schema, query_params)

        backend_query = await self.check_query(query_schema, backend_query)
        results, meta = await self.run_query(query_schema, backend_query)

        return self.process_result(results, meta)

    def construct_query(self, query_schema, query_params):
        """ Convert from the frontend query to the backend query """

        query_scope = query_schema.base_query(query_params)
        return BackendQuery.create(
            identifier=query_params.identifier,
            scope=query_scope,
            where=query_params.args,
            limit=query_params.limit,
            offset=query_params.offset,
            select=query_params.select,
            sort=query_params.sort
        )

    async def run_query(self, query_schema, backend_query: BackendQuery):
        """ Execute the backend query with the state manager and return """
        return backend_query, None

    async def check_query(self, query_schema, backend_query):
        return backend_query

    def process_result(self, results, metadata):
        return results, metadata

    def serialize_data(self, data):
        return data


class PgQueryHandler(QueryHandler):
    def __init__(self, data_manager):
        self._manager = data_manager

    @property
    def manager(self):
        return self._manager

    async def run_query(self, query_schema, backend_query: BackendQuery):
        """ Execute the backend query with the state manager and return """
        result = await self.manager.find_all(query_schema.meta.backend_resource, backend_query)
        return list(result), None

    async def check_query(self, query_schema, backend_query):
        return backend_query
