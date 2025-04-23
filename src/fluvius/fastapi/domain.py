from typing import Annotated, Union, Any, Optional, Dict
from types import SimpleNamespace
from fluvius.domain import Domain
from fluvius.data import UUID_TYPE, DataModel, UUID_GENR
from fluvius.domain.manager import DomainManager
from fluvius.domain.context import DomainContext, DomainTransport
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Path, Body
from . import logger, config

IDEMPOTENCY_KEY = config.RESP_HEADER_IDEMPOTENCY
URI_SEP = '/'
SCOPING_SEP = '~'

def uri(*elements):
    return  URI_SEP.join(('',) + elements)


def parse_scoping(scoping_stmt):
    def _parse(stmt):
        if not stmt:
            return

        for part in stmt.split(URI_SEP):
            key, _, value = part.partition(SCOPING_SEP)
            yield (key or 'domain_sid', value)

    return dict(_parse(scoping_stmt))


class FastAPIDomainManager(DomainManager):
    def __init__(self, app):
        self.initialize_domains(app)
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


        if cmd_cls.Meta.new_resource:
            if cmd_cls.Meta.normal:
                async def command_handler(request: Request, payload: PayloadType, resource: str):
                    identifier = UUID_GENR()
                    return await _command_handler(request, payload, resource, identifier, {})

                command_handler.__doc__ = cmd_cls.__doc__
                command_handler.__name__ = cmd_cls.__name__
                app.post(uri(fq_name, "{resource}", "~new"))(command_handler)

            if cmd_cls.Meta.scoped:
                async def scoped_command_handler(request: Request, payload: PayloadType, resource: str, scoping: str):
                    identifier = UUID_GENR()
                    scope = parse_scoping(scoping)
                    return await _command_handler(request, payload, resource, identifier, scope)

                scoped_command_handler.__doc__ = cmd_cls.__doc__
                scoped_command_handler.__name__ = cmd_cls.__name__
                app.post(uri(fq_name, "{scoping:path}", "{resource}", "~new"))(scoped_command_handler)
        else:
            if cmd_cls.Meta.normal:
                async def command_handler(
                    request: Request,
                    payload: PayloadType,
                    resource: str,
                    identifier: UUID_TYPE
                ):
                    return await _command_handler(request, payload, resource, identifier, {})

                command_handler.__doc__ = cmd_cls.__doc__
                command_handler.__name__ = cmd_cls.__name__
                app.post(uri(fq_name, "{resource}", "{identifier}"))(command_handler)

            if cmd_cls.Meta.scoped:
                async def scoped_command_handler(request: Request, payload: PayloadType, resource: str, identifier: UUID_TYPE, scoping: str):
                    scope = parse_scoping(scoping)
                    return await _command_handler(request, payload, resource, identifier, scope)

                scoped_command_handler.__doc__ = cmd_cls.__doc__
                scoped_command_handler.__name__ = cmd_cls.__name__
                app.post(uri(fq_name, "{scoping:path}", "{resource}", "{identifier}"))(scoped_command_handler)


    def query_handler(self, namespace, command, handler):
        uri_resource_default = f'/{namespace}.{query}/{{resource}}/'
        uri_resource_scoped  = f'/{namespace}.{query}/{{scoping:path}}/{{resource}}/'

        uri_item_default = f'/{namespace}:{command}/{{resource}}/{{identifier}}'
        uri_item_scoped  = f'/{namespace}:{command}/{{scoping:path}}/{{resource}}/{{identifier}}'


# class FluviusDomainMiddleware(BaseHTTPMiddleware):
#     def __init__(self, app, domain_manager):
#         super().__init__(app)
#         self._dm = domain_manager

#     def get_auth_context(self, request):
#         # You can optionally decode and validate the token here
#         if not (id_token := request.cookies.get("id_token")):
#             return None

#         try:
#             user = request.session.get("user")
#             if not user:
#                 return None
#         except (KeyError, ValueError):
#             return None

#         return SimpleNamespace(
#             user = user,
#             token = id_token
#         )

#     async def dispatch_func(self, request: Request, call_next):
#         try:
#             request.state.auth_context = self.get_auth_context(request)
#         except Exception as e:
#             logger.exception(e)
#             raise

#         response = await call_next(request)

#         if idem_key := request.headers.get(IDEMPOTENCY_KEY):
#             response.headers[IDEMPOTENCY_KEY] = idem_key

#         return response


def configure_domain_support(app, *domains, **kwargs):
    FastAPIDomainManager.register_domain(*domains, **kwargs)
    FastAPIDomainManager(app)
    # app.add_middleware(
    #     FluviusDomainMiddleware,
    #     domain_manager=FastAPIDomainManager(app)
    # )
    return app


