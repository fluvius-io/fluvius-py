import os
import json
from functools import wraps, partial

from pipe import Pipe
from typing import Annotated, Union, Any, Optional, Dict
from types import MethodType
from fastapi import Request, Path, Body, Query
from fluvius.query import QueryParams, FrontendQuery, QueryResourceMeta, QueryManager
from fluvius.helper import load_class

from . import logger, config
from .auth import auth_required
from .helper import uri, jurl_data, parse_scopes, SCOPES_SELECTOR, PATH_QUERY_SELECTOR


def register_resource_endpoints(app, query_manager, query_resource):
    query_id = query_resource._identifier
    base_uri = f"/{query_manager.Meta.prefix}.{query_id}/"
    api_tags = query_resource.Meta.tags or query_manager.Meta.tags
    api_docs = query_resource.Meta.desc or query_manager.Meta.desc
    scope_schema = (query_resource.Meta.scope_required or query_resource.Meta.scope_optional)

    async def resource_query(auth_ctx, query_params: QueryParams, path_query: str=None, scopes: str=None):
        query = fe_query and fe_query.query
        if isinstance(query, str):
            query = json.loads(query)

        if path_query:
            pa = jurl_data(path_query)
            if not query:
                query = params
            else:
                query = {":and": [query, params]}

        if scope_schema:
            scopes = parse_scopes(scopes, scope_schema)
            if query_resource.Meta.scope_required and not scopes:
                raise ForbiddenError('Q01-49939', f"Scoping is required for resource: {query_resource}")
        elif scopes:
            raise BadRequestError('Q01-00383', f'Scoping is not allowed for resource: {query_resource}')

        query_params = FrontendQuery.from_query_params(params, scopes=scopes, query=query)

        data, meta = await query_manager.query_resource(auth_ctx, query_id, query_params)
        return {
            'data': data,
            'meta': meta
        }

    async def item_query(auth_ctx, item_identifier, scopes: str=None):
        query_params = QueryParams.create(scopes=scopes)
        if scope_schema:
            scopes = parse_scopes(scopes, scope_schema)
            if query_resource.Meta.scope_required and not scopes:
                raise ForbiddenError('Q01-49939', f"Scoping is required for resource: {query_resource}")
        elif scopes:
            raise BadRequestError('Q01-00383', f'Scoping is not allowed for resource: {query_resource}')

        return await query_manager.query_item(auth_ctx, query_id, item_identifier, query_params)

    def endpoint(*paths, method=app.get, base=base_uri, auth={}, **kwargs):
        api_path = uri(base, *paths)
        api_meta = {"tags": api_tags, "description": api_docs} | kwargs
        api_decorator = method(api_path, **api_meta)
        if not query_resource.Meta.auth_required:
            return api_decorator

        auth_decorator = auth_required(**auth)
        def _api_def(func):
            return auth_decorator(api_decorator(func))

        return _api_def

    if query_resource.Meta.allow_list_view:
        if scope_schema:
            @endpoint(
                SCOPES_SELECTOR, PATH_QUERY_SELECTOR, "",
                summary=query_resource.Meta.name,
                description=query_resource.Meta.desc)  # "" for trailing slash
            async def query_resource_scoped(request: Request, path_query: Annotated[str, Path()], scopes: str):
                ctx = getattr(request.state, 'auth_context', None)
                return await resource_query(ctx, None, path_query, scopes)

            @endpoint(SCOPES_SELECTOR, "",
                summary=query_resource.Meta.name,
                description=query_resource.Meta.desc)  # "" for trailing slash
            async def query_resource_scoped_json(request: Request, query_params: Annotated[QueryParams, Query()], scopes: str):
                ctx = getattr(request.state, 'auth_context', None)
                return await resource_query(ctx, query_params, None, scopes)

        @endpoint(PATH_QUERY_SELECTOR, "",
                summary=query_resource.Meta.name,
                description=query_resource.Meta.desc)
        async def query_resource_json(request: Request, path_query: Annotated[str, Path()], query_params: Annotated[QueryParams, Query()]):
            ctx = getattr(request.state, 'auth_context', None)
            return await resource_query(ctx, None, path_query, None)

        @endpoint("",
                summary=query_resource.Meta.name,
                description=query_resource.Meta.desc) # Trailing slash
        async def query_resource_default(request: Request, query_params: Annotated[QueryParams, Query()]):
            ctx = getattr(request.state, 'auth_context', None)
            return await resource_query(ctx, query_params, None, None)

    if query_resource.Meta.allow_meta_view:
        @endpoint(base=f"/_meta{base_uri}", summary=f"Query Metadata [{query_resource.Meta.name}]", tags=["Metadata"])
        async def query_info(request: Request) -> dict:
            return query_resource.specs()

    if query_resource.Meta.allow_item_view:
        @endpoint("{identifier}",
                summary=f"{query_resource.Meta.name} (Item)",
                description=query_resource.Meta.desc)
        async def query_item_default(request: Request, identifier: Annotated[str, Path()]):
            ctx = getattr(request.state, 'auth_context', None)
            return await item_query(ctx, identifier, scopes=scopes)

        if scope_schema:
            @endpoint(SCOPES_SELECTOR, "{identifier}",
                summary=f"{query_resource.Meta.name} (Item)",
                description=query_resource.Meta.desc)
            async def query_item_scoped(request: Request, identifier: Annotated[str, Path()], scopes: str):
                ctx = getattr(request.state, 'auth_context', None)
                return await item_query(ctx, identifier, scopes=scopes)


def regsitery_manager_endpoints(app, query_manager):

    def endpoint(path, method=app.get, authorization=True, **kwargs):
        api_path = f"/{query_manager.Meta.prefix}{path}"
        api_decorator = method(api_path, **kwargs)

        if not authorization:
            return api_decorator

        auth_params = authorization if isinstance(authorization, dict) else {}
        auth_decorator = auth_required(**auth_params)

        def _decorator(func):
            return auth_decorator(api_decorator(func))

        return _decorator

    for api_url, (func, kwargs) in query_manager.endpoint_registry.items():
        handler = MethodType(func, query_manager)
        endpoint(
            api_url,
            tags=query_manager.Meta.tags,
            description=func.__doc__,
            **kwargs
        )(handler)

def register_query_manager(app, qm_cls):
    query_manager = qm_cls(app)

    regsitery_manager_endpoints(app, query_manager)
    for _, query_resource in query_manager.resource_registry.items():
        register_resource_endpoints(app, query_manager, query_resource)

@Pipe
def configure_query_manager(app, *query_managers):
    @app.get(uri("/_meta/_echo", SCOPES_SELECTOR, PATH_QUERY_SELECTOR, "{identifier}"), tags=["Metadata"])
    async def query_echo(query_params: Annotated[QueryParams, Query()], scopes, path_query, identifier):
        return {
            "identifier": identifier,
            "query_params": query_params,
            "scopes": parse_scopes(scopes),
            "path_query": jurl_data(path_query)
        }

    for qm_spec in query_managers:
        qm_cls = load_class(qm_spec, base_class=QueryManager)
        register_query_manager(app, qm_cls)

    return app
