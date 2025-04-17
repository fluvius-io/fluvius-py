from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from . import config

def create_app(*args, **kwargs):
    app = FastAPI(*args, **kwargs)
    app.add_middleware(
        SessionMiddleware,
        secret_key=config.APPLICATION_SECRET_KEY,
        session_cookie=config.SESSION_COOKIE,
        https_only=config.COOKIE_HTTPS_ONLY,
        same_site=config.COOKIE_SAME_SITE_POLICY
    )

    return app

