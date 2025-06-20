import os


from typing import Annotated, Union, Any, Optional, Dict
from types import SimpleNamespace
from fastapi import Request, Path, Body, Query
from fluvius.data import UUID_TYPE, DataModel, UUID_GENR
from fluvius.data.serializer import serialize_json
from fluvius.domain import Domain
from fluvius.domain.context import DomainContext, DomainTransport
from fluvius.domain.manager import DomainManager
from fluvius.query import FrontendQuery, QueryResourceMeta
from fluvius.query.helper import scope_decoder
from fluvius.helper import load_class
from pipe import Pipe

from . import logger, config
from .auth import auth_required
from .helper import uri, SCOPE_SELECTOR


class FastAPIDomainManager(DomainManager):
    def __init__(self, app):
        self.initialize_domains(app)
        tags = []
        for domain in self._domains:
            metadata_uri = f"/_meta/{domain.__namespace__}/"
            tags.append({
                "name": domain.Meta.name,
                "description": domain.Meta.desc,
                "externalDocs": {
                    "description": "Metadata",
                    "url": f"http://localhost:8000{metadata_uri}"
                }
            })

            @app.get(metadata_uri, summary=f"Domain Metadata [{domain.Meta.name}]", tags=['Metadata'])
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
        summary=cmd_cls.Meta.name,
        description=cmd_cls.Meta.desc,
        tags=domain.Meta.tags
    )

    def endpoint(*paths, method=app.post, auth={}, **kwargs):
        api_decorator = method(uri(f"/{fq_name}", *paths), **(endpoint_info | kwargs))
        if not cmd_cls.Meta.auth_required:
            return api_decorator

        auth_decorator = auth_required(**auth)
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
            authorization=getattr(request.state, 'auth_context', None),
            headers=dict(request.headers),
            transport=DomainTransport.FASTAPI,
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
            @endpoint("{resource}", ":new", summary=cmd_cls.Meta.name, description=cmd_cls.Meta.desc)
            async def command_handler(
                request: Request,
                payload: PayloadType,
                resource: Annotated[str, Path(description=cmd_cls.Meta.resource_desc)]
            ):
                identifier = UUID_GENR()
                return await _command_handler(request, payload, resource, identifier, {})

        if scope_schema:
            @endpoint(SCOPE_SELECTOR, "{resource}", ":new", summary=f"{cmd_cls.Meta.name} (Scoped)", description=cmd_cls.Meta.desc)
            async def scoped_command_handler(
                request: Request,
                payload: PayloadType,
                resource: Annotated[str, Path(description=cmd_cls.Meta.resource_desc)],
                scoping: Annotated[str, Path(description=f"Resource scoping: `{', '.join(scope_keys)}`. E.g. `~domain_sid:H9cNmGXLEc8NWcZzSThA9S`")]
            ):
                identifier = UUID_GENR()
                scope = scope_decoder(scoping, scope_schema)
                return await _command_handler(request, payload, resource, identifier, scope)

        return app

    if default_path:
        @endpoint("{resource}", "{identifier}", summary=cmd_cls.Meta.name, description=cmd_cls.Meta.desc)
        async def command_handler(
            request: Request,
            payload: PayloadType,
            resource: Annotated[str, Path(description=cmd_cls.Meta.resource_desc)],
            identifier: Annotated[UUID_TYPE, Path(description="Resource identifier")],
        ):
            return await _command_handler(request, payload, resource, identifier, {})

    if scope_schema:
        @endpoint(SCOPE_SELECTOR, "{resource}", "{identifier}", summary=f"{cmd_cls.Meta.name} (Scoped)", description=cmd_cls.Meta.desc)
        async def scoped_command_handler(
            request: Request,
            payload: PayloadType,
            resource: Annotated[str, Path(description=cmd_cls.Meta.resource_desc)],
            identifier: Annotated[UUID_TYPE, Path(description="Resource identifier")],
            scoping: Annotated[str, Path(description=f"Resource scoping: `{', '.join(scope_keys)}`. E.g. `domain_sid~H9cNmGXLEc8NWcZzSThA9S`")]
        ):
            scope = scope_decoder(scoping, scope_schema)
            return await _command_handler(request, payload, resource, identifier, scope)

    return app

@Pipe
def configure_domain_manager(app, *domains, **kwargs):
    FastAPIDomainManager.setup_app(app, *domains, **kwargs)
    return app

