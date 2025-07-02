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
        def setup_domain(domain):
            metadata_uri = f"/_meta/{domain.__namespace__}/"
            cmd_details = {
                cmd['id']: cmd for cmd in
                (
                    register_command_handler(app, *params)
                    for params in self.enumerate_command_handlers(domain)
                ) if cmd is not None
            }

            @app.get(metadata_uri, summary=f"Domain Metadata [{domain.Meta.name}]", tags=['Metadata'])
            async def domain_metadata(request: Request, details: bool=False):
                if details:
                    return domain.metadata(details = cmd_details)

                return domain.metadata()

            return {
                "name": domain.Meta.name,
                "description": domain.Meta.desc,
                "externalDocs": {
                    "description": "Metadata",
                    "url": f"http://localhost:8000{metadata_uri}"
                }
            }


        tags = [setup_domain(domain) for domain in self._domains]
        app.openapi_tags = app.openapi_tags or []
        app.openapi_tags.extend(tags)


    @classmethod
    def setup_app(cls, app, *domains, **kwargs):
        cls.register_domain(*domains, **kwargs)
        return cls(app)


def register_command_handler(app, domain, cmd_cls, cmd_key, fq_name):
    if cmd_cls.Meta.internal:
        # Note: Internal commands are not exposed to the API, registered for worker only.
        return None

    PayloadType = cmd_cls.Data if issubclass(cmd_cls.Data, DataModel) else Dict

    scope_schema = (cmd_cls.Meta.scope_required or cmd_cls.Meta.scope_optional)
    unscoped_path = bool(not cmd_cls.Meta.scope_required)
    endpoint_info = dict(
        summary=cmd_cls.Meta.name,
        description=cmd_cls.Meta.desc,
        tags=domain.Meta.tags
    )

    def endpoint(*paths, base=f"/{fq_name}", method=app.post, auth={}, **kwargs):
        api_decorator = method(uri(base, *paths), **(endpoint_info | kwargs))
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
        identifier: Optional[UUID_TYPE] = None,
        scope: Optional[dict] = None
    ) -> Any:
        identifier = identifier or UUID_GENR()
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

        responses = await domain.process_command(command, context=context)
        return {
            "data": responses,
            "status": "OK"
        }


    cmd_endpoints = {'meta': f"/_meta/{fq_name}/"}
    if scope_schema:
        scope_keys = list(scope_schema.keys())

    @endpoint(
        base=f"/_meta/{fq_name}/",
        method=app.get,
        summary=cmd_cls.Meta.name,
        description=cmd_cls.Meta.desc, tags=["Metadata"])
    async def command_metadata(request: Request):
        return cmd_metadata

    identifier_spec = "{identifier}"
    if cmd_cls.Meta.new_resource:
        identifier_spec = ":new"

    if unscoped_path:
        cmd_endpoints['path'] = uri(f"/{fq_name}", "{resource}", identifier_spec)
        @endpoint(
            "{resource}",
            identifier_spec,
            summary=cmd_cls.Meta.name,
            description=cmd_cls.Meta.desc
        )
        async def command_handler(
            request: Request,
            payload: PayloadType,
            resource: Annotated[str, Path(description=cmd_cls.Meta.resource_desc)],
            identifier: Optional[UUID_TYPE] = None,
        ):
            return await _command_handler(request, payload, resource, identifier, {})

    if scope_schema:
        cmd_endpoints['scoped'] = uri(f"/{fq_name}", SCOPE_SELECTOR, "{resource}", identifier_spec)
        @endpoint(
            SCOPE_SELECTOR,
            "{resource}",
            identifier_spec,
            summary=f"{cmd_cls.Meta.name} (Scoped)",
            description=cmd_cls.Meta.desc
        )
        async def scoped_command_handler(
            request: Request,
            payload: PayloadType,
            resource: Annotated[str, Path(description=cmd_cls.Meta.resource_desc)],
            scoping: Annotated[str, Path(description=f"Resource scoping: `{', '.join(scope_keys)}`. E.g. `domain_sid~H9cNmGXLEc8NWcZzSThA9S`")],
            identifier: Annotated[UUID_TYPE, Path(description="Resource identifier")],
        ):
            scope = scope_decoder(scoping, scope_schema)
            return await _command_handler(request, payload, resource, identifier, scope)


    cmd_metadata ={
        "id": cmd_cls.Meta.key,
        "schema": cmd_cls.Data.model_json_schema(),
        "urls": cmd_endpoints,
        "name": cmd_cls.Meta.name,
        "desc": cmd_cls.Meta.desc,
        "genid": cmd_cls.Meta.new_resource
    }

    return cmd_metadata

@Pipe
def configure_domain_manager(app, *domains, **kwargs):
    FastAPIDomainManager.setup_app(app, *domains, **kwargs)
    return app

