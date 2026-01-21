import os


from typing import Annotated, Union, Any, Optional, Dict
from types import SimpleNamespace
from fastapi import Request, Path, Body, Query
from fluvius.data import UUID_TYPE, DataModel, UUID_GENR
from fluvius.data.serializer import serialize_json
from fluvius.domain import Domain
from fluvius.domain.context import DomainContext, DomainTransport, DomainServiceProxy
from fluvius.domain.manager import DomainManager
from fluvius.query import FrontendQuery, QueryResourceMeta
from fluvius.query.helper import scope_decoder
from fluvius.helper import load_class
from fluvius.error import InternalServerError
from pipe import Pipe

from . import logger, config
from .auth import auth_required
from .helper import uri, SCOPE_SELECTOR


class FastAPIDomainManager(DomainManager):
    def __init__(self, app):
        super().__init__()
        self._app = app
    
    @property
    def app(self):
        return self._app

    def setup_domain_endpoints(self):
        self.initialize_domains(self.app)
        def _setup_domain(domain):
            namespace = domain.Meta.namespace
            metadata_uri = f"/_meta/{namespace}/"
            cmd_details = {
                cmd['key']: cmd for cmd in
                (
                    register_command_handler(self.app, *params)
                    for params in self._enumerate_command_handlers(domain)
                ) if cmd is not None
            }

            @self.app.get(metadata_uri, summary=f"Domain Metadata [{domain.Meta.name}]", tags=['Metadata'])
            async def domain_metadata(request: Request):
                return domain.metadata(commands = cmd_details)

            return {
                "id": namespace,
                "name": namespace,
                "description": domain.Meta.description,
                "externalDocs": {
                    "description": "Metadata",
                    "url": f"http://localhost:8000{metadata_uri}"
                }
            }

        tags = [_setup_domain(domain) for domain in self._domains]
        self.app.openapi_tags = self.app.openapi_tags or []
        self.app.openapi_tags.extend(tags)


    @classmethod
    def setup_app(cls, app, *domains, **kwargs):
        if hasattr(app.state, 'domain_manager'):
            raise InternalServerError("S00.301", "Domain manager already initialized")
        
        manager = cls(app)
        manager.register_domain(*domains, **kwargs)
        manager.setup_domain_endpoints()
        app.state.domain_manager = manager
        return app


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
        payload: PayloadType,  # type: ignore
        resource: str,
        identifier: Optional[UUID_TYPE] = None,
        scope: Optional[dict] = None
    ) -> Any:
        identifier = identifier or UUID_GENR()
        
        with domain.session(
            authorization=getattr(request.state, 'auth_context', None),
            headers=dict(request.headers),
            transport=DomainTransport.FASTAPI,
            source=request.client.host,
            service_proxy=DomainServiceProxy(app.state)
        ):

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

            responses = await domain.process_command(command)
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
    if cmd_cls.Meta.resource_init:
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
            payload: PayloadType,  # type: ignore
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
            payload: PayloadType,  # type: ignore
            resource: Annotated[str, Path(description=cmd_cls.Meta.resource_desc)],
            scoping: Annotated[str, Path(description=f"Resource scoping: `{', '.join(scope_keys)}`. E.g. `domain_sid~H9cNmGXLEc8NWcZzSThA9S`")],
            identifier: Annotated[UUID_TYPE, Path(description="Resource identifier")],
        ):
            scope = scope_decoder(scoping, scope_schema)
            return await _command_handler(request, payload, resource, identifier, scope)


    cmd_metadata ={
        "key": cmd_cls.Meta.key,
        "name": cmd_cls.Meta.name,
        "description": cmd_cls.Meta.desc,
        "schema": cmd_cls.Data.model_json_schema(),
        "urls": cmd_endpoints,
        "genid": cmd_cls.Meta.resource_init
    }

    return cmd_metadata

@Pipe
def configure_domain_manager(app, *domains, **kwargs):
    FastAPIDomainManager.setup_app(app, *domains, **kwargs)
    return app

