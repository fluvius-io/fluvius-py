from fastapi import FastAPI, Request
from starlette.middleware.sessions import SessionMiddleware
from .domain import configure_domain_support
from .profiler import configure_profiler

from . import config, logger

def create_app(config=config, **kwargs):
    app = FastAPI(**kwargs)
    @app.get("/~/app-summary")
    async def status_resp(request: Request):
        return {
            "name": modcfg.APPLICATION_NAME,
            "serial_no": modcfg.APPLICATION_SERIAL_NUMBER,
            "build_time": modcfg.APPLICATION_BUILD_TIME,
        }

    configure_domain_support(app)
    configure_session(app, config)

    return app



def configure_session(app, config=config):
    # Last middleware added execute first
    app.add_middleware(
        SessionMiddleware,
        secret_key=config.APPLICATION_SECRET_KEY,
        session_cookie=config.SESSION_COOKIE,
        https_only=config.COOKIE_HTTPS_ONLY,
        same_site=config.COOKIE_SAME_SITE_POLICY
    )

    return app
