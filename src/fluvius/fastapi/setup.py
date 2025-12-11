import traceback
import fluvius
from fluvius.error import FluviusException
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import ResponseValidationError
from functools import wraps
from pydantic import ValidationError

from . import config, logger

_on_startups = tuple()
_on_shutdowns = tuple()


def on_startup(*func):
    global _on_startups
    _on_startups += func
    return func


def on_shutdown(*func):
    global _on_shutdowns
    _on_shutdowns += func
    return func


@asynccontextmanager
async def lifespan(app: FastAPI):
    for func in _on_startups:
        await func(app)

    yield

    for func in _on_shutdowns:
        await func(app)


def create_app(config=config, **kwargs) -> FastAPI:
    cfg = dict(
        title=config.APPLICATION_NAME,
        version=config.APPLICATION_VERSION,
        description=config.APPLICATION_DESC,
        root_path=config.APPLICATION_ROOT
    )
    cfg.update(kwargs)
    app = FastAPI(lifespan=lifespan, **cfg)

    @app.get("/_meta", tags=["Metadata"])
    async def application_metadata(request: Request):
        ''' Basic information of the API application '''
        return {
            "name": config.APPLICATION_NAME,
            "version": config.APPLICATION_VERSION,
            "framework": fluvius.__version__,
            "build_no": config.APPLICATION_SERIAL_NUMBER,
            "build_time": config.APPLICATION_BUILD_TIME,
        }

    return setup_error_handler(app)


def setup_error_tracker(app: FastAPI) -> FastAPI:
    from fluvius.error.tracker import ErrorTracker

    tracker_name = config.ERROR_TRACKER
    tracker = ErrorTracker.get_tracker(tracker_name)
    original_handler = app.exception_handler

    def tracker_handler(exc_class_or_status_code):
        def decorator(func):
            @wraps(func)
            async def wrapper(request, exc, *args, **kwargs):
                tracker.capture_exception(exc)
                return await func(request, exc, *args, **kwargs)
            return original_handler(exc_class_or_status_code)(wrapper)
        return decorator

    app.exception_handler = tracker_handler
    return app


def setup_error_handler(app: FastAPI) -> FastAPI:
    DEVELOPER_MODE = config.DEVELOPER_MODE

    if config.ERROR_TRACKER:
        app = setup_error_tracker(app)

    @app.exception_handler(FluviusException)
    async def fluvius_exception_handler(request: Request, exc: FluviusException):
        content = exc.content

        if DEVELOPER_MODE:
            content = exc.content or {}
            content['traceback'] = traceback.format_exc()

        return JSONResponse(
            status_code=exc.status_code,
            content=content
        )
    
    @app.exception_handler(ValidationError)
    async def validation_error_exception_handler(request: Request, exc: ValidationError):
        content = {
            "errcode": "A422.01",
            "details": exc.errors(),
            "message": str(exc),
        }
        
        if DEVELOPER_MODE:
            content['traceback'] = traceback.format_exc()

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=content
        )

    @app.exception_handler(ValueError)
    async def value_error_exception_handler(request: Request, exc: ValueError):
        content = {
            "message": str(exc),
            "errcode": "A400.01",
        }

        if DEVELOPER_MODE:
            content['traceback'] = traceback.format_exc()

        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=content
        )

    @app.exception_handler(RuntimeError)
    async def runtime_error_exception_handler(request: Request, exc: RuntimeError):
        content = {
            "message": str(exc),
            "errcode": "A422.02",
        }

        if DEVELOPER_MODE:
            content['traceback'] = traceback.format_exc()

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=content
        )

    @app.exception_handler(ResponseValidationError)
    async def response_validation_exception_handler(request: Request, exc: ResponseValidationError):
        logger.error(f"Response validation failed: {exc}")
        content = {
            "message": "Internal Server Error - Response Validation Failed",
            "errcode": "A500.02",
            "details": str(exc.errors()),
        }

        if DEVELOPER_MODE:
            content['traceback'] = traceback.format_exc()

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=content
        )
    
    return app

def setup_kcadmin(app):
    from .kcadmin import KCAdmin
    KCAdmin(
        app=app,
        server_url=config.KEYCLOAK_BASE_URL,
        client_id=config.KEYCLOAK_CLIENT_ID,
        client_secret=config.KEYCLOAK_CLIENT_SECRET,
        realm_name=config.KEYCLOAK_REALM
    )

    return app
