import fluvius
from fluvius.error import FluviusException
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from . import config, logger

def create_app(config=config, **kwargs):
    cfg = dict(
        title=config.APPLICATION_NAME,
        version=config.APPLICATION_VERSION,
        description=config.APPLICATION_DESC
    )
    cfg.update(kwargs)
    app = FastAPI(lifespan=lifespan, **cfg)

    @app.get("/_metadata", tags=["Metadata"])
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

def setup_error_handler(app):
    @app.exception_handler(FluviusException)
    async def app_exception_handler(request: Request, exc: FluviusException):
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.content
        )

    @app.exception_handler(ValueError)
    async def app_exception_handler(request: Request, exc: ValueError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"message": str(exc), "errcode": "A00422"}
        )

    return app

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
