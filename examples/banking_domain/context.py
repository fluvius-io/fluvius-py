from fluvius.domain.context import Context
from fluvius.domain.record import field
from sanic import Sanic


class SanicContext(Context):
    app = field(type=Sanic)
