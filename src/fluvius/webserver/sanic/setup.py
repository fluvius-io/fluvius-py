from fluvius.domain.context import DomainTransport

from sanic import Sanic
from sanic.response import json

from fluvius.helper.timeutil import timestamp
from .context import SanicContext, SanicDomainServiceProxy

from . import config, logger

IDEMPOTENCY_KEY = config.IDEMPOTENCY_KEY


def create_server(modcfg, configure_logging=False, **kwargs):
    app = Sanic(modcfg.APPLICATION_NAME, configure_logging=configure_logging, **kwargs)
    app.config.update(config.as_dict())
    app.config.update(modcfg.as_dict())

    configure_sanic_profiler(app)
    configure_domain_support(app)

    @app.route("/~/app-summary")
    async def status_resp(request):
        return json({
            "name": modcfg.APPLICATION_NAME,
            "serial_no": modcfg.APPLICATION_SERIAL_NUMBER,
            "build_time": modcfg.APPLICATION_BUILD_TIME,
        })

    return app


def configure_sanic_profiler(app):
    if not config.ENABLE_PROFILER:
        return app

    from pyinstrument import Profiler
    from sanic.response import html

    @app.on_request
    async def start_profiler(request):
        if "_profile" in request.args:
            request.ctx.profiler = Profiler()
            request.ctx.profiler.start()

    @app.on_response
    async def stop_profiler(request, response):
        if not hasattr(request.ctx, "profiler"):
            return

        request.ctx.profiler.stop()
        output_html = request.ctx.profiler.output_html()
        return html(output_html)

    return app


def configure_domain_support(app):
    initial_context = SanicContext(
        # Attach request object for later reference
        # TODO: Depreciate this line or define a proper interface for CQRS Request
        source=app.name,
        serial=app.config.APPLICATION_SERIAL_NUMBER,
        transport=DomainTransport.SANIC
    )

    def get_domain_context(request):
        ctx = request.ctx
        return initial_context.set(
            timestamp=timestamp(),
            user_id=req_ctx.user_id,
            profile_id=req_ctx.profile_id,
            organization_id=req_ctx.organization_id
        )

    def get_service_proxy(request):
        pass

    @app.on_response(priority=100)
    def add_idempotency_key(request, response):
        response.headers[IDEMPOTENCY_KEY] = request.headers.get(IDEMPOTENCY_KEY)

    app.ctx.domain_context = get_domain_context
    app.ctx.service_proxy = get_service_proxy

    return app
