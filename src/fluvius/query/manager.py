import sqlalchemy
import jsonurl_py

from types import MethodType
from typing import Optional, List, Dict, Any
from fluvius.auth import AuthorizationContext
from fluvius.data import BackendQuery, DataModel
from fluvius.helper import camel_to_lower, select_value
from fluvius.error import InternalServerError, NotFoundError, ForbiddenError
from fluvius.casbin import PolicyRequest
from .resource import QueryResource, FrontendQuery
from ._meta import config, logger


def _compute_select(query_select, query_resource):
    if query_resource.Meta.select_all:
        return query_select  # Either none, or as-is

    if not query_select:
        return query_resource.select_fields

    return query_resource.select_fields & set(query_select)


class QueryManagerMeta(DataModel):
    name: str
    prefix: str
    tags: Optional[List[str]] = None
    desc: Optional[str] = None


class QueryManager(object):
    __resources__    = None
    __endpoints__    = None
    __data_manager__ = None

    class Meta:
        pass

    def __init_subclass__(cls, data_manager=None):
        super().__init_subclass__()

        if cls.__dict__.get('__abstract__'):
            return

        cls.__data_manager__ = select_value(data_manager, cls.__data_manager__)
        cls.__resources__ = {}
        cls.__endpoints__ = {}

        cls.Meta = QueryManagerMeta.create(cls.Meta, defaults={
            'name': cls.__name__,
            'prefix': camel_to_lower(cls.__name__),
            'desc': (cls.__doc__ or '').strip(),
            'tags': [cls.__name__,]
        })

    @property
    def resource_registry(self):
        return self.__resources__

    @property
    def endpoint_registry(self):
        return self.__endpoints__

    @classmethod
    def lookup_query_resource(cls, identifier):
        return cls.__resources__[identifier]

    @classmethod
    def lookup_query_endpoint(self, identifier):
        return cls.__endpoints__[identifier]

    @classmethod
    def register_endpoint(cls, uri, **kwargs):
        def _decorator(func):
            cls.__endpoints__[uri] = (func, kwargs)
            return func

        return _decorator

    @classmethod
    def validate_query_resource(cls, schema_cls):
        if issubclass(schema_cls, QueryResource):
            return schema_cls

        raise ValueError(f'Invalid query model: {schema_cls}')

    @classmethod
    def register_resource(cls, query_identifier):
        def _decorator(schema_cls):
            if getattr(schema_cls, '_identifier', None):
                raise ValueError(f'QueryResource already registered with identifier: {schema_cls._identifier}')

            schema_cls._identifier = query_identifier
            if query_identifier in cls.__resources__:
                raise ValueError(f'Resource identifier is already registered: {query_identifier} => {schema_cls}')

            query_resource = cls.validate_query_resource(schema_cls)
            cls.__resources__[query_identifier] = query_resource()
            return query_resource

        return _decorator

    def validate_fe_query(self, query_resource, fe_query):
        if not isinstance(fe_query, FrontendQuery):
            raise ValueError(f'Invalid query: {fe_query}')

        return fe_query

    async def query_resource(self, query_identifier: str, fe_query: FrontendQuery, auth_ctx: Optional[AuthorizationContext]=None):
        query_resource = self.lookup_query_resource(query_identifier)

        fe_query = self.validate_fe_query(query_resource, fe_query)
        pl_scope = await self.authorize_by_policy(query_resource, fe_query, auth_ctx=auth_ctx)
        be_query = self.construct_backend_query(query_resource, fe_query, auth_ctx=auth_ctx, policy_scope=pl_scope)
        data, meta = await self.execute_query(query_resource, be_query, meta={}, auth_ctx=auth_ctx)

        return self.process_result(data, meta)

    async def query_item(self, query_identifier: str, item_identifier, fe_query: FrontendQuery, auth_ctx: Optional[AuthorizationContext]=None):
        query_resource = self.lookup_query_resource(query_identifier)
        fe_query = self.validate_fe_query(query_resource, fe_query)
        pl_scope = await self.authorize_by_policy(query_resource, fe_query, item_identifier, auth_ctx=auth_ctx)
        be_query = self.construct_backend_query(query_resource, fe_query, item_identifier, auth_ctx=auth_ctx, policy_scope=pl_scope)
        data, meta = await self.execute_query(query_resource, be_query, auth_ctx=auth_ctx)

        result, _ = self.process_result(data, meta)

        if len(result) == 0:
            raise NotFoundError("Q102-501", f"Item not found!", None)

        return result[0]

    async def query_endpoint(self, endpoint_identifier, **kwargs):
        func, _params = self.lookup_query_endpoint(endpoint_identifier)
        handler = MethodType(func, self)
        return handler(**kwargs)

    async def authorize_by_policy(self, query_resource, fe_query, identifier=None, auth_ctx=None):
        qmeta = query_resource.Meta
        base_scope = query_resource.base_query(auth_ctx, fe_query.scope)

        if not self.__policymgr__ or not qmeta.policy_required or not auth_ctx:
            return base_scope

        try:
            res = fe_query.scope["resource"]
            rid = fe_query.scope["resource_id"]
            actx = auth_ctx
            reqs = PolicyRequest(
                usr=actx.user._id,
                sub=actx.profile._id,
                org=actx.organization._id,
                dom=self.Meta.prefix,
                res=res,
                rid=rid,
                act=query_resource._identifier
            )
            resp = await self._policymgr.check_permission(reqs)
            logger.info("QUERY PERMISSION RESPONSE: %r" % resp)
            if not resp.allowed:
                raise ForbiddenError('Q4031212', f'Permission Failed: [{resp.narration}]')

            auth_scope = []
            for policy in resp.narration.policies:
                if policy.role == 'sys-admin':
                    return base_scope

                if policy.meta:
                    if not isinstance(policy.meta, str):
                        raise ForbiddenError('Q4031213', f'{policy.meta} must be str with jsonurl format.')

                    format_meta = policy.meta.format(**reqs.serialize())
                    scope_meta = jsonurl_py.loads(format_meta)
                    auth_scope.append(scope_meta)

            scope = [_scope for _scope in [auth_scope, base_scope] if _scope]

            if not scope:
                return None

            return {".and": scope}
        except (jsonurl_py.ParseError, KeyError) as e:
            raise InternalServerError('Q4031215', f"Interal Error: {e}")

    def construct_backend_query(self, query_resource: str, fe_query, /, identifier=None, auth_ctx: Optional[AuthorizationContext]=None, policy_scope=None):
        """ Convert from the frontend query to the backend query """
        scope   = policy_scope
        query   = query_resource.generate_query_statement(fe_query.user_query, fe_query.path_query)
        limit   = fe_query.limit
        offset  = (fe_query.page - 1) * fe_query.limit
        select  = _compute_select(fe_query.select, query_resource)

        backend_query = BackendQuery.create(
            identifier=identifier,
            limit=limit,
            offset=offset,
            scope=scope,
            select=select,
            sort=fe_query.sort,
            where=query,
            mapping=query_resource.query_mapping
        )
        return self.validate_backend_query(query_resource, backend_query)

    async def execute_query(
        self,
        query_resource: str,
        backend_query: BackendQuery,
        /,
        meta: Optional[Dict] = None,
        auth_ctx: Optional[AuthorizationContext]=None):
        """ Execute the backend query with the state manager and return """
        raise NotImplementedError('QueryResource.execute_query')

    def validate_backend_query(self, query_resource, backend_query):
        return backend_query

    def process_result(self, data, meta):
        return data, meta


class DomainQueryManager(QueryManager):
    __abstract__ = True
    __policymgr__ = None

    def __init__(self, app=None):
        self._app = app
        self._data_manager = self.__data_manager__(app)

        if self.__policymgr__:
            self._policymgr = self.__policymgr__(self._data_manager)

    @property
    def data_manager(self):
        return self._data_manager

    @property
    def policymgr(self):
        return self._policymgr

    async def execute_query(
        self,
        query_resource: str,
        backend_query: BackendQuery,
        /,
        meta: Optional[Dict] = None,
        auth_ctx: Optional[AuthorizationContext]=None):
        """ Execute the backend query with the state manager and return """
        resource = query_resource.backend_model()
        try:
            data = await self.data_manager.query(resource, backend_query, return_meta=meta)
        except (
            sqlalchemy.exc.ProgrammingError,
            sqlalchemy.exc.DBAPIError
        ) as e:
            details = None if not config.DEVELOPER_MODE else {
                "pgcode": getattr(e.orig, 'pgcode', None),
                "statement": e.statement,
                "params": e.params,
            }

            raise InternalServerError("Q101-501", f"Query Error [{getattr(e.orig, 'pgcode', None)}]: {e.orig}", details)

        return data, meta
