import os

from typing import Annotated, Union, Any, Optional, Dict
from fastapi import Request, Path, Body, Query
from fluvius.query.schema import FrontendQueryParams
from fluvius.query.schema import QuerySchemaMeta

from . import logger, config
from .auth import auth_required
from .helper import uri, jurl_data, parse_scopes


def register_query_schema(app, qm_cls, query_schema):
    base_uri = f"/{qm_cls.Meta.api_prefix}.{query_schema._identifier}/"
    api_tags = query_schema.Meta.api_tags or qm_cls.Meta.api_tags
    api_docs = query_schema.Meta.api_docs or qm_cls.Meta.api_docs
    scope_schema = (query_schema.Meta.scope_required or query_schema.Meta.scope_optional)

    async def _query_handler(query_params: FrontendQueryParams, path_query: str=None, scopes: str=None):
        if path_query:
            params = jurl_data(path_query)
            query_params = FrontendQueryParams(**params)

        data, meta = await manager.query(query_id, query_params)
        return {
            'data': data,
            'meta': meta
        }

    def endpoint(*paths, method=app.get, **kwargs):
        api_decorator = method(uri(base_uri, *paths), tags=api_tags, description=api_docs)
        if not query_schema.Meta.auth_required:
            return api_decorator

        auth_decorator = auth_required(**kwargs)
        def _api_def(func):
            return api_decorator(auth_decorator(func))

        return _api_def

    if query_schema.Meta.allow_list_view:
        if scope_schema:
            @endpoint("~{scopes}", "{path_query}/")
            async def query_scoped_resource(path_query: Annotated[str, Path()], scopes: str):
                return await _query_handler(None, path_query, scopes)

            @endpoint("~{scopes}/")
            async def query_scoped_resource_json(query_params: Annotated[FrontendQueryParams, Query()], scopes: str):
                return await _query_handler(query_params, None, scopes)

        @endpoint("{path_query}/")
        async def query_resource_json(path_query: Annotated[str, Path()]):
            return await _query_handler(None, path_query, None)

        @endpoint()
        async def query_resource(query_params: Annotated[FrontendQueryParams, Query()]):
            return await _query_handler(query_params, None, None)

    if query_schema.Meta.allow_meta_view:
        @endpoint(":queryinfo")
        async def query_info(request: Request) -> QuerySchemaMeta:
            return query_schema.Meta

    if query_schema.Meta.allow_item_view:
        @endpoint("{identifier}")
        async def query_item(identifier: Annotated[str, Path()]):
            return [identifier, query_params]

        if scope_schema:
            @endpoint("~{scopes}", "{identifier}")
            async def query_scoped_item(identifier: Annotated[str, Path()], scopes: Annotated[str, Path()]):
                return [identifier, scopes]


def register_query_manager(app, qm_cls):
    manager = qm_cls(app)

    for _, query_schema in qm_cls._registry.items():
        register_query_schema(app, qm_cls, query_schema)


def configure_query_manager(app, *query_managers):
    for qm_cls in query_managers:
        register_query_manager(app, qm_cls)

    return app
