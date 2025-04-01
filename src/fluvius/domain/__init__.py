from fluvius.data import identifier

from .cfg import config, logger
from .aggregate import Aggregate
from .command import Command, CommandState, CommandEnvelop
from .context import DomainContext
from .decorators import (
    DomainEntityType,
)
from .domain import Domain
from .event import Event
from .message import DomainMessage
from .record import DomainEntityRecord
from .response import DomainResponse
from .state import StateManager, data_query

__version__ = "1.3.0"
__all__ = (
    "Aggregate",
    "CommandEnvelop",
    "Command",
    "CommandState",
    "config",
    "DomainContext",
    "DomainEntityRecord",
    "DomainEntityType",
    "DomainMessage",
    "DomainResponse",
    "Domain",
    "Event",
    "EventProcessor",
    "field",
    "identifier",
    "logger",
    "StateManager",
)


@Domain.entity
class DefaultResponse(DomainResponse):
    pass
