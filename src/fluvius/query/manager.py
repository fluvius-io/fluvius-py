import sqlalchemy
import jsonurl_py

from types import MethodType
from typing import Optional, List, Dict, Any
from fluvius.auth import AuthorizationContext
from fluvius.data import BackendQuery, DataModel
from fluvius.helper import camel_to_lower, select_value
from fluvius.error import InternalServerError, NotFoundError, ForbiddenError, BadRequestError
from fluvius.casbin import PolicyRequest
from .resource import QueryResource
from .model import FrontendQuery
from ._meta import config, logger


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
    def lookup_query_endpoint(cls, identifier):
        return cls.__endpoints__[identifier]

    @classmethod
    def register_endpoint(cls, uri, **kwargs):
        def _decorator(func):
            cls.__endpoints__[uri] = (func, kwargs)
            return func

        return _decorator

    @classmethod
    def register_resource(cls, query_identifier):
        def _decorator(resource_cls):
            if getattr(resource_cls, '_identifier', None):
                raise BadRequestError('Q00.513', f'QueryResource already registered with identifier: {resource_cls._identifier}')

            resource_cls.initialize_resource(query_identifier)

            if query_identifier in cls.__resources__:
                raise BadRequestError('Q00.514', f'Resource identifier is already registered: {query_identifier} => {resource_cls}')

            cls.__resources__[query_identifier] = resource_cls
            return resource_cls

        return _decorator

    def validate_fe_query(self, query_resource, fe_query):
        if fe_query.text and not query_resource.Meta.allow_text_search:
            raise BadRequestError("Q00.502", f"Text search is not allowed for this resource [{query_resource.Meta.name}]")

        if not isinstance(fe_query, FrontendQuery):
            raise BadRequestError('Q00.508', f'Invalid query: {fe_query}')

        return fe_query

    async def query_resource(self, auth_ctx: Optional[AuthorizationContext], query_identifier: str, fe_query: FrontendQuery):
        query_resource = self.lookup_query_resource(query_identifier)

        fe_query = self.validate_fe_query(query_resource, fe_query)
        pl_scope = await self.authorize_by_policy(auth_ctx, query_resource, fe_query)
        be_query = self.construct_backend_query(auth_ctx, query_resource, fe_query, policy_scope=pl_scope)
        data, meta = await self.execute_query(query_resource, be_query, meta={})

        return self.process_result(data, meta)

    async def query_item(self, auth_ctx: Optional[AuthorizationContext], query_identifier: str, item_identifier, fe_query: FrontendQuery):
        query_resource = self.lookup_query_resource(query_identifier)
        fe_query = self.validate_fe_query(query_resource, fe_query)
        pl_scope = await self.authorize_by_policy(auth_ctx, query_resource, fe_query, item_identifier)
        be_query = self.construct_backend_query(auth_ctx, query_resource, fe_query, item_identifier, policy_scope=pl_scope)
        data, meta = await self.execute_query(query_resource, be_query)

        result, _ = self.process_result(data, meta)

        if len(result) == 0:
            raise NotFoundError("Q00.501", f"Item not found!", None)

        return result[0]

    async def query_endpoint(self, endpoint_identifier, **kwargs):
        func, _params = self.lookup_query_endpoint(endpoint_identifier)
        handler = MethodType(func, self)
        return handler(**kwargs)

    async def authorize_by_policy(self, auth_ctx: Optional[AuthorizationContext], query_resource, fe_query, identifier=None) -> dict:
        qmeta = query_resource.Meta
        if not config.QUERY_PERMISSION:
            return None

        if not self.__policymgr__ or not qmeta.policy_required or not auth_ctx:
            return None

        actx = auth_ctx
        act = f"{self.Meta.prefix}.{query_resource._identifier}"
        reqs = PolicyRequest(
            usr=actx.user._id,
            pro=actx.profile._id,
            org=actx.organization._id,
            act=act,
            rid=identifier or "",
            cqrs='QUERY'
        )

        async with self.data_manager.transaction():
            resp = await self._policymgr.check_permission(reqs)

        if not resp.allowed:
            raise ForbiddenError('Q00.004', f'Permission Failed: [{resp.narration}]')

        return resp.narration.restriction

    def construct_backend_query(self,
        auth_ctx: Optional[AuthorizationContext],
        query_resource: QueryResource,
        fe_query: FrontendQuery, /,
        identifier=None,
        policy_scope=None
    ):
        """ Convert from the frontend query to the backend query """

        # developer defined restrictions
        base_query = query_resource.base_query(auth_ctx, fe_query.scope)

        # consumer defined restrictions
        query      = query_resource.process_query(fe_query.user_query, fe_query.path_query, base_query)

        limit      = fe_query.limit
        offset     = (fe_query.page - 1) * fe_query.limit
        sort       = query_resource.process_sort(*fe_query.sort if fe_query.sort else tuple())
        include, exclude = query_resource.process_select(fe_query.include, fe_query.exclude)

        backend_query = BackendQuery.create(
            identifier=identifier,
            limit=limit,
            offset=offset,
            scope=policy_scope,  # frame work defined restriction of resource
            include=include,
            exclude=exclude,
            sort=sort,
            where=query,
            alias=query_resource._alias,
            text=fe_query.text,
        )

        return self.validate_backend_query(query_resource, backend_query)

    async def execute_query(
        self,
        query_resource: QueryResource,
        backend_query: BackendQuery,
        /,
        meta: Optional[Dict] = None,
    ):
        """ Execute the backend query with the state manager and return """
        raise NotImplementedError('QueryResource.execute_query')

    def validate_backend_query(self, query_resource, backend_query):
        return backend_query

    def process_result(self, data, meta):
        return data, meta

