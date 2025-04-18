from enum import IntEnum
from .mutation import MutationType  # noqa


CQRS_ENTITY_MARKER = "_domain_entity"
CQRS_ENTITY_KEY = "_domain"


class DomainEntityType(IntEnum):
    QUERY = 0
    EVENT = 1
    COMMAND = 2
    RESPONSE = 3
    MESSAGE = 4
    CONTEXT = 5
    EVT_HANDLER = 6
    CMD_HANDLER = 7
    RESOURCE = 8
    ACTIVITY_LOG = 9
    MUTATION = 10


class CommandState(IntEnum):
    SUCCESS = 0
    CREATED = 1
    PENDING = 2
    RUNNING = 3
    DENIED = 4
    REJECTED = 5
    SUBMITTED = 6
    APPLIED = 7
    ERRORED = 99
    RETRY_1 = 100
    RETRY_2 = 101
    RETRY_3 = 102
    FAILED = 500
    CANCELED = 501


class CommandAction(IntEnum):
    CREATE = 0
    UPDATE = 1
    REMOVE = 2


class EventState(IntEnum):
    SUCCESS = 0
    CREATED = 1
    PENDING = 2
    RUNNING = 3
    ERROR = 99
    RETRY_1 = 100
    RETRY_2 = 101
    RETRY_3 = 102
    FAILED = 500
    CANCELED = 501
