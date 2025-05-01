import os

from typing import Annotated, Union, Any, Optional, Dict
from types import SimpleNamespace
from fastapi import Request, Path, Body, Query
from fluvius.data import UUID_TYPE, DataModel, UUID_GENR
from fluvius.data.serializer import serialize_json
from fluvius.domain import Domain
from fluvius.domain.context import DomainContext, DomainTransport
from fluvius.domain.manager import DomainManager
from fluvius.query.schema import FrontendQueryParams
from fluvius.query.schema import QuerySchemaMeta
from starlette.middleware.base import BaseHTTPMiddleware

from . import logger, config
from .auth import auth_required
from .helper import uri, jurl_data, parse_scopes


class FastAPIDomainManager(DomainManager):
    def __init__(self, app):
        self.initialize_domains(app)
        tags = []
        for domain in self._domains:
            metadata_uri = f"/{domain.__domain__}.metadata/"
            tags.append({
                "name": domain.Meta.name,
                "description": domain.Meta.desc,
                "externalDocs": {
                    "description": "Metadata",
                    "url": f"http://localhost:8000{metadata_uri}"
                }
            })

            @app.get(metadata_uri, summary="Domain Metadata", tags=[domain.Meta.name])
            async def domain_metadata(request: Request):
                return domain.metadata()

        app.openapi_tags = app.openapi_tags or []
        app.openapi_tags.extend(tags)

        for params in self.enumerate_commands():
            register_command_handler(app, *params)

    @classmethod
    def setup_app(cls, app, *domains, **kwargs):
        cls.register_domain(*domains, **kwargs)
        return cls(app)


def register_command_handler(app, domain, cmd_cls, cmd_key, fq_name):
    PayloadType = cmd_cls.Data if issubclass(cmd_cls.Data, DataModel) else Dict

    scope_schema = (cmd_cls.Meta.scope_required or cmd_cls.Meta.scope_optional)
    default_path = bool(not cmd_cls.Meta.scope_required)
    endpoint_info = dict(
                summary=cmd_cls.Meta.name or cmd_cls.__name__,
                description=cmd_cls.__doc__,
                tags=[domain.Meta.name]
    )

    def postapi(*paths, method=app.post, **kwargs):
        api_decorator = method(uri(f"/{fq_name}", *paths), **endpoint_info)
        if not cmd_cls.Meta.auth_required:
            return api_decorator

        auth_decorator = auth_required(**kwargs)
        def _api_def(func):
            return api_decorator(auth_decorator(func))

        return _api_def

    async def _command_handler(
        request: Request,
        payload: PayloadType,
        resource: str,
        identifier: UUID_TYPE,
        scope: dict
    ) -> Any:
        context = domain.setup_context(
            headers=dict(request.headers),
            transport=DomainTransport.REDIS,
            source=request.client.host
        )

        command = domain.create_command(
            cmd_key,
            payload,
            aggroot=(
                resource,
                identifier,
                scope.get('domain_sid'),
                scope.get('domain_iid'),
            )
        )

        return await domain.process_command(command, context=context)


    if scope_schema:
        scope_keys = list(scope_schema.keys())

    if cmd_cls.Meta.new_resource:
        if default_path:
            @postapi("{resource}", ":new")
            async def command_handler(
                request: Request,
                payload: PayloadType,
                resource: Annotated[str, Path(description=cmd_cls.Meta.resource_desc)]
            ):
                identifier = UUID_GENR()
                return await _command_handler(request, payload, resource, identifier, {})

        if scope_schema:
            @postapi("~{scopes}","{resource}", ":new")
            async def scoped_command_handler(
                request: Request,
                payload: PayloadType,
                resource: Annotated[str, Path(description=cmd_cls.Meta.resource_desc)],
                scoping: Annotated[str, Path(description=f"Resource scoping: `{', '.join(scope_keys)}`. E.g. `~domain_sid:H9cNmGXLEc8NWcZzSThA9S`")]
            ):
                identifier = UUID_GENR()
                scope = parse_scopes(scoping, scope_schema)
                return await _command_handler(request, payload, resource, identifier, scope)

        return app

    if default_path:
        @postapi("{resource}", "{identifier}")
        async def command_handler(
            request: Request,
            payload: PayloadType,
            resource: Annotated[str, Path(description=cmd_cls.Meta.resource_desc)],
            identifier: Annotated[UUID_TYPE, Path(description="Resource identifier")],
        ):
            return await _command_handler(request, payload, resource, identifier, {})


    if scope_schema:
        @postapi("~{scopes}", "{resource}", "{identifier}")
        async def scoped_command_handler(
            request: Request,
            payload: PayloadType,
            resource: Annotated[str, Path(description=cmd_cls.Meta.resource_desc)],
            identifier: Annotated[UUID_TYPE, Path(description="Resource identifier")],
            scoping: Annotated[str, Path(description=f"Resource scoping: `{', '.join(scope_keys)}`. E.g. `domain_sid~H9cNmGXLEc8NWcZzSThA9S`")]
        ):
            scope = parse_scopes(scoping, scope_schema)
            return await _command_handler(request, payload, resource, identifier, scope)

    return app


def register_query_manager(app, qm_cls):
    manager = qm_cls(app)

    for query_id, query_schema in qm_cls._registry.items():
        base_uri = f"/{qm_cls.Meta.prefix}.{query_id}/"
        api_tags = query_schema.Meta.tags or qm_cls.Meta.tags
        api_docs = query_schema.Meta.desc or qm_cls.Meta.desc
        api_info = dict(tags=api_tags, description=api_docs)
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

        def api(*paths, method=app.get, **kwargs):
            api_decorator = method(uri(base_uri, *paths), **api_info)
            if not query_schema.Meta.auth_required:
                return api_decorator

            auth_decorator = auth_required(**kwargs)
            def _api_def(func):
                return api_decorator(auth_decorator(func))

            return _api_def

        if query_schema.Meta.allow_list_view:
            if scope_schema:
                @api("~{scopes}", "{path_query}/")
                async def query_scoped_resource(path_query: Annotated[str, Path()], scopes: str):
                    return await _query_handler(None, path_query, scopes)

                @api("~{scopes}/")
                async def query_scoped_resource_json(query_params: Annotated[FrontendQueryParams, Query()], scopes: str):
                    return await _query_handler(query_params, None, scopes)

            @api("{path_query}/")
            async def query_resource_json(path_query: Annotated[str, Path()]):
                return await _query_handler(None, path_query, None)

            @api("")
            async def query_resource(query_params: Annotated[FrontendQueryParams, Query()]):
                return await _query_handler(query_params, None, None)

        if query_schema.Meta.allow_meta_view:
            @api(":queryinfo")
            async def query_info(request: Request) -> QuerySchemaMeta:
                return query_schema.Meta

            @api("~{scopes}", "{path_query}", ":echo")
            async def query_echo(query_params: Annotated[FrontendQueryParams, Query()], scopes, path_query):
                return {
                    "query_params": query_params,
                    "scopes": parse_scopes(scopes),
                    "path_query": jurl_data(path_query)
                }

        if query_schema.Meta.allow_item_view:
            @api("{identifier}")
            async def query_item(identifier: Annotated[str, Path()]):
                return [identifier, query_params]

            if scope_schema:
                @api("~{scopes}", "{identifier}")
                async def query_scoped_item(identifier: Annotated[str, Path()], scopes: Annotated[str, Path()]):
                    return [identifier, scopes]


def configure_domain_manager(app, *domains, **kwargs):
    FastAPIDomainManager.setup_app(app, *domains, **kwargs)
    return app


def configure_query_manager(app, *query_managers):
    for qm_cls in query_managers:
        register_query_manager(app, qm_cls)
    return app
