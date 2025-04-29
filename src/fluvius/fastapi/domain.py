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
            register_command_handler(app, *params)


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


def register_command_handler(app, domain, cmd_cls, cmd_key, fq_name):
    PayloadType = cmd_cls.Data if issubclass(cmd_cls.Data, DataModel) else Dict

    scope_schema = (cmd_cls.Meta.scope_required or cmd_cls.Meta.scope_optional)
    default_path = bool(not cmd_cls.Meta.scope_required)
    endpoint_info = dict(
                summary=cmd_cls.Meta.name or cmd_cls.__name__,
                description=cmd_cls.__doc__,
                tags=[domain.Meta.name]
    )

    def postapi(*paths):
        return app.post(uri(*paths), **endpoint_info)

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
            @postapi(fq_name, "{resource}", ":new")
            async def command_handler(
                request: Request,
                payload: PayloadType,
                resource: Annotated[str, Path(description=cmd_cls.Meta.resource_desc)]
            ):
                identifier = UUID_GENR()
                return await _command_handler(request, payload, resource, identifier, {})

        if scope_schema:
            @postapi(fq_name, "~{scoping}","{resource}", ":new")
            async def scoped_command_handler(
                request: Request,
                payload: PayloadType,
                resource: Annotated[str, Path(description=cmd_cls.Meta.resource_desc)],
                scoping: Annotated[str, Path(description=f'Resource scoping: `{', '.join(scope_keys)}`. E.g. `~domain_sid:H9cNmGXLEc8NWcZzSThA9S`')]
            ):
                identifier = UUID_GENR()
                scope = parse_scoping(scoping, scope_schema)
                return await _command_handler(request, payload, resource, identifier, scope)

        return

    if default_path:
        @postapi(fq_name, "{resource}", "{identifier}")
        async def command_handler(
            request: Request,
            payload: PayloadType,
            resource: Annotated[str, Path(description=cmd_cls.Meta.resource_desc)],
            identifier: Annotated[UUID_TYPE, Path(description="Resource identifier")],
        ):
            return await _command_handler(request, payload, resource, identifier, {})


    if scope_schema:
        @postapi(fq_name, "~{scoping}", "{resource}", "{identifier}")
        async def scoped_command_handler(
            request: Request,
            payload: PayloadType,
            resource: Annotated[str, Path(description=cmd_cls.Meta.resource_desc)],
            identifier: Annotated[UUID_TYPE, Path(description="Resource identifier")],
            scoping: Annotated[str, Path(description=f'Resource scoping: `{', '.join(scope_keys)}`. E.g. `domain_sid~H9cNmGXLEc8NWcZzSThA9S`')]
        ):
            scope = parse_scoping(scoping, scope_schema)
            return await _command_handler(request, payload, resource, identifier, scope)


def register_query_manager(app, qm_cls):
    manager = qm_cls(app)

    for query_id, query_schema in qm_cls._registry.items():
        base_uri = f"{qm_cls.Meta.prefix}.{query_id}/"
        api_info = dict(tags=qm_cls.Meta.tags, description=query_schema.__doc__)

        async def _query_handler(query_params: FrontendQueryParams, path_params: str=None, scope: str=None):
            if path_params:
                params = jsonurl_py.loads(path_params)
                query_params = FrontendQueryParams(**params)

            data, meta = await manager.query(query_id, query_params)
            return {
                'data': data,
                'meta': meta
            }

        def getapi(*paths):
            return app.get(uri(*paths), **api_info)

        @getapi(base_uri, '~{scoping}', '{path_params}/')
        async def query_scoped_resource(path_params: Annotated[str, Path()], scope: str):
            return await _query_handler(None, path_params, scope)

        @getapi(base_uri, '{path_params}/')
        async def query_resource_json(path_params: Annotated[str, Path()]):
            return await _query_handler(None, path_params, None)

        @getapi(base_uri, '~{scoping}/')
        async def query_scoped_resource_json(query_params: Annotated[FrontendQueryParams, Query()], scope: str):
            return await _query_handler(query_params, None, scope)

        @getapi(base_uri)
        async def query_resource(query_params: Annotated[FrontendQueryParams, Query()]):
            return await _query_handler(query_params, None, None)

        @getapi(base_uri, "{identifier}")
        def query_item(identifier: Annotated[str, Path()]):
            return [identifier, query_params]

        @getapi(base_uri, "~{scoping}", "{identifier}")
        def query_item(identifier: Annotated[str, Path()], scoping: Annotated[str, Path()]):
            return [identifier, scoping]

        @getapi(base_uri, ":queryinfo")
        def query_info() -> QuerySchemaMeta:
            return query_schema._meta


def configure_domain_manager(app, *domains, **kwargs):
    FastAPIDomainManager.register_domain(*domains, **kwargs)
    app.add_middleware(FluviusDomainMiddleware, dm=FastAPIDomainManager(app))
    return app


def configure_query_manager(app, *query_managers):
    for qm_cls in query_managers:
        register_query_manager(app, qm_cls)
    return app
