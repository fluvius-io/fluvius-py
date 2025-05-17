import os
from functools import wraps

from pipe import Pipe
from typing import Annotated, Union, Any, Optional, Dict
from fastapi import Request, Path, Body, Query
from fluvius.query import FrontendQuery, QuerySchemaMeta, QueryManager
from fluvius.helper import load_class

from . import logger, config
from .auth import auth_required
from .helper import uri, jurl_data, parse_scopes, SCOPES_SELECTOR, PATH_QUERY_SELECTOR


def register_query_schema(app, query_manager, query_schema):
    query_id = query_schema._identifier
    base_uri = f"/{query_manager.Meta.api_prefix}.{query_id}/"
    api_tags = query_schema.Meta.api_tags or query_manager.Meta.api_tags
    api_docs = query_schema.Meta.api_docs or query_manager.Meta.api_docs
    scope_schema = (query_schema.Meta.scope_required or query_schema.Meta.scope_optional)

    async def _resource_query(query_params: FrontendQuery, path_query: str=None, scopes: str=None):
        if path_query:
            params = jurl_data(path_query)
            query_params = FrontendQuery(**params)

        data, meta = await query_manager.query(query_id, query_params)
        return {
            'data': data,
            'meta': meta
        }

    async def _item_query(item_identifier, path_query: str=None, scopes: str=None):
        query_params = None
        if path_query:
            params = jurl_data(path_query)
            query_params = FrontendQuery(**params)

        return await query_manager.query_item(query_id, item_identifier, query_params)

    def endpoint(*paths, method=app.get, base=None, tags=None, **kwargs):
        api_decorator = method(uri(base or base_uri, *paths), tags=tags or api_tags, description=api_docs)
        if not query_schema.Meta.auth_required:
            return api_decorator

        auth_decorator = auth_required(**kwargs)
        def _api_def(func):
            return auth_decorator(api_decorator(func))

        return _api_def

    if query_schema.functions:
        for url, func in query_schema.functions:
            async def _func(request: Request):
                return await func(request, query_manager)

            _func.__name__ = func.__name__
            _func.__doc__ = func.__doc__

            endpoint(url)(_func)

    if query_schema.Meta.allow_list_view:
        if scope_schema:
            @endpoint(SCOPES_SELECTOR, PATH_QUERY_SELECTOR, "")  # Trailing slash
            async def query_scoped_resource(path_query: Annotated[str, Path()], scopes: str):
                return await _resource_query(None, path_query, scopes)

            @endpoint(SCOPES_SELECTOR, "")
            async def query_scoped_resource_json(query_params: Annotated[FrontendQuery, Query()], scopes: str):
                return await _resource_query(query_params, None, scopes)

        @endpoint(PATH_QUERY_SELECTOR, "")
        async def query_resource_json(path_query: Annotated[str, Path()], query_params: Annotated[FrontendQuery, Query()]):
            return await _resource_query(None, path_query, None)

        @endpoint("") # Trailing slash
        async def query_resource(query_params: Annotated[FrontendQuery, Query()]):
            return await _resource_query(query_params, None, None)

    if query_schema.Meta.allow_meta_view:
        @endpoint(base=f"/_info{base_uri}", tags=["Introspection"])
        async def query_info(request: Request) -> QuerySchemaMeta:
            return query_schema.Meta

    if query_schema.Meta.allow_item_view:
        @endpoint("{identifier}")
        async def query_item(identifier: Annotated[str, Path()]):
            return await _item_query(identifier)

        if scope_schema:
            @endpoint(SCOPES_SELECTOR, "{identifier}")
            async def query_scoped_item(identifier: Annotated[str, Path()], scopes: str):
                return await _item_query(identifier)


def register_query_manager(app, qm_cls):
    query_manager = qm_cls(app)

    for _, query_schema in qm_cls._registry.items():
        register_query_schema(app, query_manager, query_schema)

@Pipe
def configure_query_manager(app, *query_managers):
    @app.get(uri("/_echo", SCOPES_SELECTOR, PATH_QUERY_SELECTOR, "{identifier}"), tags=["Introspection"])
    async def query_echo(query_params: Annotated[FrontendQuery, Query()], scopes, path_query, identifier):
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
