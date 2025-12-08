from enum import IntEnum
from fluvius.domain import logger
from fluvius.data import BlankModel, DataModel
from fluvius.helper import camel_to_title, camel_to_lower
from .mutation import MutationType  # noqa


DOMAIN_ENTITY_MARKER = "__entity_marker__"
DOMAIN_ENTITY_KEY = "__entity_key__"


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


class DomainEntity(object):
    __meta_schema__ = BlankModel

    class Data(DataModel):
        pass

    class Meta(BlankModel):
        pass

    def __init_subclass__(cls):
        if cls.__dict__.get('__abstract__'):
            return

        # Get the metadata of the current class, not of its parents.
        cls_meta = cls.__dict__.get('Meta')
        if cls_meta is not None:
            cls_meta = cls_meta.__dict__
        else:
            cls_meta = {}

        # 1. Parent meta objects,
        # 2. default values for current class
        # 3. Custom meta defined by the class itself
        meta = cls.Meta.__dict__ | {
            "key": camel_to_lower(cls.__name__),
            "name": camel_to_title(cls.__name__),
            "desc": cls.__doc__
        } | cls_meta

        cls.Meta = cls.__meta_schema__(**meta)

        if not issubclass(cls.Data, (DataModel, BlankModel)):
            logger.warning(f'Unsupported Entity Data Model: {cls.__name__} => {cls.Data}')


