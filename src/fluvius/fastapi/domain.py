import os
from typing import Annotated, Union, Any, Optional, Dict
from types import SimpleNamespace
from fluvius.domain import Domain
from fluvius.data import UUID_TYPE, DataModel, UUID_GENR
from fluvius.domain.manager import DomainManager
from fluvius.domain.context import DomainContext, DomainTransport
from fluvius.data.serializer import serialize_json
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Path, Body, Query
from fluvius.query.schema import QuerySchemaMeta
from fluvius.query.schema import FrontendQueryParams
import jsonurl_py
from . import logger, config

IDEMPOTENCY_KEY = config.RESP_HEADER_IDEMPOTENCY
URI_SEP = '/'
SCOPING_SEP = '~'

def uri(*elements):
    return os.path.join("/", *elements)


def parse_scoping(scoping_stmt, scope_schema):
    def _parse():
        if not stmt:
            return

        for part in scoping_stmt.split(SCOPING_SEP):
            if not part:
                continue

            key, sep, value = part.partition(':')
            if sep == '' and value == '':
                value = key
                key = 'domain_sid'

            if key == '':
                key = 'domain_sid'

            if key not in scope_schema:
                yield (key, value)
            else:
                yield (key, scope_schema[key](value))

    return dict(_parse())


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
            self._register_handler(app, *params)

    def _register_handler(self, app, domain, cmd_cls, cmd_key, fq_name):
        PayloadType = cmd_cls.Data if issubclass(cmd_cls.Data, DataModel) else Dict

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


        scope_schema = (cmd_cls.Meta.scope_required or cmd_cls.Meta.scope_optional)
        default_path = bool(not cmd_cls.Meta.scope_required)
        endpoint_info = dict(
                    summary=cmd_cls.Meta.name or cmd_cls.__name__,
                    description=cmd_cls.__doc__,
                    tags=[domain.Meta.name]
        )
        if scope_schema:
            scope_keys = list(scope_schema.keys())

        if cmd_cls.Meta.new_resource:
            if default_path:
                async def command_handler(
                    request: Request,
                    payload: PayloadType,
                    resource: Annotated[str, Path(description=cmd_cls.Meta.resource_desc)]
                ):
                    identifier = UUID_GENR()
                    return await _command_handler(request, payload, resource, identifier, {})

                app.post(uri(fq_name, "{resource}", ":new"), **endpoint_info)(command_handler)

            if scope_schema:
                async def scoped_command_handler(
                    request: Request,
                    payload: PayloadType,
                    resource: Annotated[str, Path(description=cmd_cls.Meta.resource_desc)],
                    scoping: Annotated[str, Path(description=f'Resource scoping: `{', '.join(scope_keys)}`. E.g. `~domain_sid:H9cNmGXLEc8NWcZzSThA9S`')]
                ):
                    identifier = UUID_GENR()
                    scope = parse_scoping(scoping, scope_schema)
                    return await _command_handler(request, payload, resource, identifier, scope)

                app.post(uri(fq_name, "~{scoping}", "{resource}", ":new"), **endpoint_info)(scoped_command_handler)
        else:
            if default_path:
                async def command_handler(
                    request: Request,
                    payload: PayloadType,
                    resource: Annotated[str, Path(description=cmd_cls.Meta.resource_desc)],
                    identifier: Annotated[UUID_TYPE, Path(description="Resource identifier")],
                ):
                    return await _command_handler(request, payload, resource, identifier, {})

                app.post(
                    uri(fq_name, "{resource}", "{identifier}"), **endpoint_info
                )(command_handler)

            if scope_schema:
                async def scoped_command_handler(
                    request: Request,
                    payload: PayloadType,
                    resource: Annotated[str, Path(description=cmd_cls.Meta.resource_desc)],
                    identifier: Annotated[UUID_TYPE, Path(description="Resource identifier")],
                    scoping: Annotated[str, Path(description=f'Resource scoping: `{', '.join(scope_keys)}`. E.g. `domain_sid~H9cNmGXLEc8NWcZzSThA9S`')]
                ):
                    scope = parse_scoping(scoping, scope_schema)
                    return await _command_handler(request, payload, resource, identifier, scope)

                app.post(uri(fq_name, "~{scoping}", "{resource}", "{identifier}"), **endpoint_info)(scoped_command_handler)


class FluviusDomainMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, dm):
        super().__init__(app)
        self._dm = dm

    def get_auth_context(self, request):
        # You can optionally decode and validate the token here
        if not (id_token := request.cookies.get("id_token")):
            return None

        try:
            user = request.session.get("user")
            if not user:
                return None
        except (KeyError, ValueError):
            return None

        return SimpleNamespace(
            user = user,
            token = id_token
        )

    async def dispatch(self, request: Request, call_next):
        try:
            request.state.auth_context = self.get_auth_context(request)
        except Exception as e:
            logger.exception(e)
            raise

        response = await call_next(request)

        if idem_key := request.headers.get(IDEMPOTENCY_KEY):
            response.headers[IDEMPOTENCY_KEY] = idem_key

        return response


def configure_domain_manager(app, *domains, **kwargs):
    FastAPIDomainManager.register_domain(*domains, **kwargs)
    app.add_middleware(FluviusDomainMiddleware, dm=FastAPIDomainManager(app))
    return app

def setup_query_manager(app, qm_cls):
    manager = qm_cls(app)

    for query_id, query_schema in qm_cls._registry.items():
        base_uri = f"{qm_cls.Meta.prefix}.{query_id}/"
        api_info = dict(tags=qm_cls.Meta.tags, description=query_schema.__doc__)

        async def _query_handler(query_params: FrontendQueryParams, path_params: str=None, scope: str=None):
            # data = jsonurl_py.loads(path_params) if path_params else None
            data, meta = await manager.query(query_id, query_params)
            return {
                'query': query_params,
                'data': data,
                'meta': meta
            }

        @app.get(uri(base_uri, '~{scoping}', '{path_params}/'), **api_info)
        async def query_scoped_resource(query_params: Annotated[FrontendQueryParams, Query()], path_params: Annotated[Optional[str], Path()], scope: str):
            return await _query_handler(query_params, path_params, scope)

        @app.get(uri(base_uri, '{path_params}/'), **api_info)
        async def query_resource_json(query_params: Annotated[FrontendQueryParams, Query()], path_params: Annotated[Optional[str], Path()]):
            return await _query_handler(query_params, path_params, None)

        @app.get(uri(base_uri, '~{scoping}/'), **api_info)
        async def query_scoped_resource_json(query_params: Annotated[FrontendQueryParams, Query()], scope: str):
            return await _query_handler(query_params, None, scope)

        @app.get(uri(base_uri), **api_info)
        async def query_resource(query_params: Annotated[FrontendQueryParams, Query()]):
            return await _query_handler(query_params, None, None)

        @app.get(uri(base_uri, ":queryinfo"), **api_info)
        def query_info() -> QuerySchemaMeta:
            return query_schema._meta

        @app.get(uri(base_uri, "{identifier}"), **api_info)
        @app.get(uri(base_uri, "~{scoping}", "{identifier}"), **api_info)
        def query_item(identifier: Annotated[str, Path()]):
            return [identifier, query_params]

def configure_query_manager(app, *query_managers):
    for qm_cls in query_managers:
        setup_query_manager(app, qm_cls)
    return app
