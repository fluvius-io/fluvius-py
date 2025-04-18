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

    def get_domain_context(self, request):
        auth_ctx = request.state.auth_context
        if not auth_ctx:
            return None

        return self.base_context.set(
                user_id = auth_ctx.user["sub"]
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
    def _wrap_command(self, domain, cmd_key, qual_name):
        async def _command_handler(
            request: Request,
            resource: str,
            identifier: UUID_TYPE=None,
            domain_sid: UUID_TYPE=None,
            domain_iid: UUID_TYPE=None
        ):
            domain_ctx = request.state.domain_context
            command_payload = request.json()
            command_aggroot = AggregateRoot(resource, identifier, domain_sid, domain_iid)
            command = domain.create_command(
                cmd_key,
                command_payload,
                command_aggroot
            )

            return await domain.process_command(domain_ctx, command)
        _command_handler.__name__ = f"{cmd_key}_handler"
        return _command_handler


def configure_domain_support(app, config=config):
    manager = FastAPIDomainManager(app)

    app.add_middleware(DomainMiddleware, DomainContext(
        source=config.APPLICATION_TITLE,
        serial=config.APPLICATION_SERIAL_NUMBER,
        transport=DomainTransport.SANIC
    ))
    for namespace, command, handler in manager.enumerate_command_handlers():
        uri_pattern = f'/{namespace}:{command}/{{resource}}/{{identifier}}'
        uri_pattern_sid = f'/{namespace}:{command}/~{{domain_sid}}:{{domain_iid}}/{{resource}}/{{identifier}}'
        handler = app.get(uri_pattern)(handler)
        handler = app.get(uri_pattern_sid)(handler)
    return app


