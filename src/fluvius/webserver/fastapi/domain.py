from types import SimpleNamespace
from fluvius.domain import Domain
from fluvius.data import UUID_TYPE
from fluvius.domain.manager import DomainManager
from fluvius.domain.context import DomainContext, DomainTransport
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from . import logger, config

IDEMPOTENCY_KEY = config.RESP_HEADER_IDEMPOTENCY

class DomainMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, base_context):
        super(DomainMiddleware, self).__init__(app)
        self.base_context = base_context

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
            request.state.domain_context = self.get_domain_context(request)
        except Exception as e:
            logger.exception(e)
            raise

        response = await call_next(request)

        if idem_key := request.headers.get(IDEMPOTENCY_KEY):
            response.headers[IDEMPOTENCY_KEY] = idem_key

        return response


class FastAPIDomainManager(DomainManager):
    def __init__(self, app):
        self.initialize_domains(app)
        tuple(
            self._register_handler(app, *params)
            for params in self.enumerate_commands()
        )

    def _generate_handler(self, domain, qual_name, cmd_key, cmd_cls):
        async def _handle_request(request: Request, resource, identifier=None, scoping=None):
            context = domain.setup_context(
                headers=request.headers,
                transport=DomainTransport.REDIS,
                source=request.context.source
            )

            cmddata = request.command
            command = domain.create_command(
                cmd_key,
                cmddata.payload,
                aggroot=(
                    cmddata.resource,
                    cmddata.identifier,
                    cmddata.domain_sid,
                    cmddata.domain_iid
                )
            )

            return await domain.process_command(command, context=context)

        return _handle_request


def fast_api_resource_command_handler(namespace, command, handler):
    cmd_normal = f'/{namespace}:{command}'
    cmd_scoped = f'/{namespace}:{command}/{{scoping:path}}'

    uri_resource = '{cmd_normal}/{{resource}}/'
    uri_resource_scoped  = f'/{namespace}:{command}/{{scoping:path}}/{{resource}}/'

    uri_item_default = f'/{namespace}:{command}/{{resource}}/{{identifier}}'
    uri_item_scoped  = f'/{namespace}:{command}/{{scoping:path}}/{{resource}}/{{identifier}}'

    def _handler(resource: str, scoping: str=None, identifier=None):
        # parse payload
        payload = None
        # parse aggroot
        aggroot = None
        return handler(command, payload, aggroot)


def fast_api_query_handler(namespace, command, handler):
    uri_resource_default = f'/{namespace}~{query}/{{resource}}/'
    uri_resource_scoped  = f'/{namespace}~{query}/{{scoping:path}}/{{resource}}/'

    uri_item_default = f'/{namespace}:{command}/{{resource}}/{{identifier}}'
    uri_item_scoped  = f'/{namespace}:{command}/{{scoping:path}}/{{resource}}/{{identifier}}'



def configure_domain_support(app, config=config):
    manager = FastAPIDomainManager(app)

    app.add_middleware(DomainMiddleware, DomainContext(
        source=config.APPLICATION_TITLE,
        serial=config.APPLICATION_SERIAL_NUMBER,
        transport=DomainTransport.SANIC
    ))
    for namespace, command, handler in manager.enumerate_command_handlers():
        uri_pattern = f'/{namespace}:{command}/{{resource}}/{{identifier}}'
        uri_pattern_sid = f'/{namespace}~{{domain_sid}}:{command}/{{resource}}/{{identifier}}'
        # uri_pattern_sid = f'/{namespace}~{{domain_sid}}~{{query}}/{{resource}}/{{identifier}}'
        handler = app.get(uri_pattern)(handler)
        handler = app.get(uri_pattern_sid)(handler)
        logger.warning('Registered: %s => %s', uri_pattern, str((namespace, command, handler)))
    return app


