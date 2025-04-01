from datetime import datetime

from fluvius.domain.context import DomainTransport

from sanic import Sanic
from sanic.response import json
from fluvius_connector.sentry import configure_sentry
from fluvius_swagger import configure_sanic_swagger
from fluvius_toolbox import configure_toolbox

from fluvius.sanic import config
from .context import SanicContext, SanicDomainServiceProxy

IDEMPOTENCY_KEY = config.IDEMPOTENCY_KEY


def create_app(module, configure_logging=False, **kwargs):
    modcfg = module.config
    app = Sanic(modcfg.APPLICATION_NAME, configure_logging=configure_logging, **kwargs)
    app.ctx.__namespace__ = module.__name__
    app.ctx.__version__ = module.__version__
    app.config.update(modcfg.as_dict())

    configure_profiler(app)

    configure_toolbox(app)
    configure_sentry(app, release_version=f"{modcfg.APPLICATION_NAME} @ {module.__version__}")
    configure_sanic_swagger(app)
    configure_domain(app)

    # @TODO: this is not generic enough and may break (i.e. query vs command)
    @app.route("/~app-summary")
    async def status_resp(request):
        return json({
            "application": module.__name__,
            "version": module.__version__,
            "timestamp": str(datetime.utcnow())
        })

    return app


def configure_profiler(app):
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


def configure_domain(app, revision=1):
    initial_context = SanicContext.create(
        _service_proxy=SanicDomainServiceProxy(app),
        # Attach request object for later reference
        # TODO: Depreciate this line or define a proper interface for CQRS Request
        namespace=app.name,
        revision=revision,
        source=config.CQRS_SOURCE,
        transport=DomainTransport.SANIC
    )

    @app.on_request(priority=100)
    def add_domain_context(request):
        request.ctx.domain_context = initial_context.set(
            timestamp=datetime.utcnow(),
            _request=request,
            _session=request.cookies.get("session")
        )

    @app.on_response(priority=100)
    def add_idempotency_key(request, response):
        response.headers[IDEMPOTENCY_KEY] = request.headers.get(IDEMPOTENCY_KEY)

    return app
