from ._meta import config, logger
from .aggregate import Aggregate
from .command import Command, CommandState, CommandBundle
from .context import DomainContext
from .decorators import (
    DomainEntityType,
)
from .domain import Domain
from .event import Event
from .message import MessageRecord
from .record import DomainEntityRecord
from .response import DomainResponse
from .state import StateManager, data_query
from .model import ImmutableDomainResource

__all__ = (
    "Aggregate",
    "CommandBundle",
    "Command",
    "CommandState",
    "config",
    "DomainContext",
    "DomainEntityRecord",
    "DomainEntityType",
    "MessageRecord",
    "DomainResponse",
    "Domain",
    "Event",
    "EventProcessor",
    "field",
    "identifier",
    "logger",
    "StateManager",
)


@Domain.response
class DefaultResponse(DomainResponse):
    pass
