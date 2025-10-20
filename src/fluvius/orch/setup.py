from contextlib import asynccontextmanager
from hatchet_sdk import Hatchet

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
async def lifespan(worker: Hatchet):
    for func in _on_startups:
        await func(worker)

    yield

    for func in _on_shutdowns:
        await func(worker)
