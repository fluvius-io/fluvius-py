import fluvius

from fastapi import FastAPI, Request
from starlette.middleware.sessions import SessionMiddleware
from .profiler import configure_profiler

from . import config, logger

def create_app(config=config, **kwargs):
    cfg = dict(
        title=config.APPLICATION_NAME,
        version=config.APPLICATION_VERSION,
        description=config.APPLICATION_DESC
    )
    cfg.update(kwargs)
    app = FastAPI(**cfg)

    app.add_middleware(
        SessionMiddleware,
        secret_key=config.APPLICATION_SECRET_KEY,
        session_cookie=config.SESSION_COOKIE,
        https_only=config.COOKIE_HTTPS_ONLY,
        same_site=config.COOKIE_SAME_SITE_POLICY
    )

    @app.get("/~metadata", tags=["Metadata"])
    async def application_metadata(request: Request):
        ''' Basic information of the API application '''
        return {
            "name": config.APPLICATION_NAME,
            "version": config.APPLICATION_VERSION,
            "framework": fluvius.__version__,
            "build_no": config.APPLICATION_SERIAL_NUMBER,
            "build_time": config.APPLICATION_BUILD_TIME,
        }

    return app


