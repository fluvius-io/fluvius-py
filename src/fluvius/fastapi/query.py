import re
from functools import wraps, partial

from pipe import Pipe
from typing import Annotated, Union, Any, Optional, Dict, List
from types import MethodType
from pydantic import BaseModel
from fastapi import Request, Path, Body, Query
from fluvius.query.helper import scope_decoder
from fluvius.query import QueryParams, FrontendQuery, QueryResourceMeta, QueryManager
from fluvius.helper import load_class
from fluvius.error import ForbiddenError, BadRequestError

from . import logger, config
from .auth import auth_required
from .helper import uri, SCOPE_SELECTOR, PATH_QUERY_SELECTOR
from pydantic import BaseModel


def register_resource_endpoints(app, query_manager, query_resource):
    query_id = query_resource._identifier
    meta = query_resource.Meta

    base_uri = f"/{query_manager.Meta.prefix}.{query_id}/"
    api_tags = meta.tags or query_manager.Meta.tags
    api_docs = meta.desc or query_manager.Meta.desc
    scope_schema = (meta.scope_required or meta.scope_optional)

    if meta.strict_response:
        class ListResultSchema(BaseModel):
            data: List[query_resource]
            meta: Dict
    else:
        ListResultSchema = None

    async def resource_query(request: Request, query_params: QueryParams, path_query: str=None, scope: str=None):
        auth_ctx = getattr(request.state, 'auth_context', None)

        if not scope_schema and scope:
            raise BadRequestError('Q01-00383', f'Scoping is not allowed for resource: {query_resource}')

        fe_query = FrontendQuery.from_query_params(query_params, scope=scope, scope_schema=scope_schema, path_query=path_query)

        if meta.scope_required and not fe_query.scope:
            raise ForbiddenError('Q01-49939', f"Scoping is required for resource: {query_resource}")

        data, page = await query_manager.query_resource(auth_ctx, query_id, fe_query)
        return {
            'data': data,
            'pagination': page
        }

    async def item_query(request: Request, item_identifier, scope: str=None):
        auth_ctx = getattr(request.state, 'auth_context', None)
        if not scope_schema and scope:
            raise BadRequestError('Q01-00383', f'Scoping is not allowed for resource: {query_resource}')

        fe_query = FrontendQuery.from_query_params(QueryParams(), scope=scope, scope_schema=scope_schema)

        if meta.scope_required and not fe_query.scope:
            raise ForbiddenError('Q01-49939', f"Scoping is required for resource: {query_resource}")

        return await query_manager.query_item(auth_ctx, query_id, item_identifier, fe_query)

    def endpoint(*paths, method=app.get, base=base_uri, auth={}, **kwargs):
        api_path = uri(base, *paths)
        api_meta = {"tags": api_tags, "description": api_docs} | kwargs
        api_decorator = method(api_path, **api_meta)
        if not meta.auth_required:
            return api_decorator

        auth_decorator = auth_required(**auth)
        def _api_def(func):
            return auth_decorator(api_decorator(func))

        return _api_def

    if meta.allow_list_view:
        list_params = dict(
            summary=meta.name,
            description=meta.desc,
            response_model=ListResultSchema
        )
        if scope_schema:
            @endpoint(
                SCOPE_SELECTOR, PATH_QUERY_SELECTOR, "", **list_params
                )  # "" for trailing slash
            async def query_resource_scoped(request: Request, path_query: Annotated[str, Path()], scope:  Annotated[str, Path()]):
                return await resource_query(request, None, path_query, scope)

            @endpoint(SCOPE_SELECTOR, "", **list_params)  # "" for trailing slash
            async def query_resource_scoped_json(request: Request, query_params: Annotated[QueryParams, Query()], scope: Annotated[str, Path()]):
                return await resource_query(request, query_params, None, scope)
            
        if not meta.scope_required:
            @endpoint(PATH_QUERY_SELECTOR, "", **list_params)
            async def query_resource_json(request: Request, path_query: Annotated[str, Path()], query_params: Annotated[QueryParams, Query()]):
                return await resource_query(request, query_params, path_query, None)

            @endpoint("", **list_params) # Trailing slash
            async def query_resource_default(request: Request, query_params: Annotated[QueryParams, Query()]):
                return await resource_query(request, query_params, None, None)

    if meta.allow_meta_view:
        @endpoint(base=f"/_meta{base_uri}", summary=f"Query Metadata [{meta.name}]", tags=["Metadata"])
        async def query_info(request: Request) -> dict:
            return query_resource.resource_meta()

    if meta.allow_item_view:
        if meta.strict_response:
            ItemResultSchema = query_resource
        else:
            ItemResultSchema = None

        item_params = dict(
            summary=f"{meta.name} (Item)",
            description=meta.desc,
            response_model=ItemResultSchema)
        
        if not meta.scope_required:
            @endpoint("{identifier}", **item_params)
            async def query_item_default(request: Request, identifier: Annotated[str, Path()]):
                item = await item_query(request, identifier)
                return item

        if scope_schema:
            @endpoint(SCOPE_SELECTOR, "{identifier}", **item_params)
            async def query_item_scoped(request: Request, identifier: Annotated[str, Path()], scope: Annotated[str, Path()]):
                # return query_resource(**(await item_query(request, identifier, scope=scope)).__dict__)
                return await item_query(request, identifier, scope=scope)


def register_manager_endpoints(app, query_manager):

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

    register_manager_endpoints(app, query_manager)
    for _, query_resource in query_manager.resource_registry.items():
        register_resource_endpoints(app, query_manager, query_resource)
    
    return app

@Pipe
def configure_query_manager(app, *query_managers):
    @app.get(uri("/_meta/_echo", SCOPE_SELECTOR, PATH_QUERY_SELECTOR, "{identifier}"), tags=["Metadata"])
    async def query_echo(query_params: Annotated[QueryParams, Query()], scope: Annotated[str, Path()], path_query: Annotated[str, Path()], identifier: Annotated[str, Path()]):
        """
        This endpoint can be used to inspect how the url search params being parsed into structure query for the backend.

        E.g:
        ```json
        $ curl "http://localhost:8000/_meta/_echo/:abc%3A38182/~xyz%3Atuv/12838383812?limit=25&page=1&select=abcdef%2Cghijkl&sort=abc.desc%2Cxyz.asc&query=%7B%22abcdef%22%3A%22ghijkl%22%7D" | jq
        {
          "identifier": "12838383812",
          "parsed_query": {
            "limit": 25,
            "page": 1,
            "select": [
              "abcdef",
              "ghijkl"
            ],
            "sort": [
              "abc.desc",
              "xyz.asc"
            ],
            "user_query": {
              "abcdef": "ghijkl"
            },
            "path_query": {
              "xyz": "tuv"
            },
            "scope": null
          },
          "query_params": {
            "limit": 25,
            "page": 1,
            "select": "abcdef,ghijkl",
            "sort": "abc.desc,xyz.asc",
            "query": "{\"abcdef\":\"ghijkl\"}"
          }
        }
        ```
        """

        fe_query = FrontendQuery.from_query_params(query_params, scope=scope, path_query=path_query)
        return {
            "identifier": identifier,
            "parsed_query": fe_query,
            "query_params": query_params,
        }

    for qm_spec in query_managers:
        qm_cls = load_class(qm_spec, base_class=QueryManager)
        register_query_manager(app, qm_cls)

    return app
