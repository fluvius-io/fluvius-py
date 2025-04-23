from fastapi import FastAPI, Request
from starlette.middleware.sessions import SessionMiddleware
from .profiler import configure_profiler

from . import config, logger

def create_app(config=config, **kwargs):
    app = FastAPI(**kwargs)

    app.add_middleware(
        SessionMiddleware,
        secret_key=config.APPLICATION_SECRET_KEY,
        session_cookie=config.SESSION_COOKIE,
        https_only=config.COOKIE_HTTPS_ONLY,
        same_site=config.COOKIE_SAME_SITE_POLICY
    )

    @app.get("/~/app-summary")
    async def status_resp(request: Request):
        return {
            "name": config.APPLICATION_TITLE,
            "serial_no": config.APPLICATION_SERIAL_NUMBER,
            "build_time": config.APPLICATION_BUILD_TIME,
        }

    return app


