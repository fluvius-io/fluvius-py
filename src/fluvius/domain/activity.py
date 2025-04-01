import enum

from .datadef import ResourceReference, field, UUID_GENR, UUID_TYPE, nullable, identifier_factory
from .record import DomainEntityRecord


class ActivityType(enum.Enum):
    USER_ACTION = 0
    APP_REQUEST = 1
    SYSTEM_CALL = 2


class ActivityLog(DomainEntityRecord):
    domain      = field(type=str, mandatory=True)
    resource    = field(type=str, mandatory=True)
    identifier  = field(type=UUID_TYPE, mandatory=True, factory=identifier_factory)
    etag        = field(type=bool, initial=False, mandatory=True)

    # Domain closure ID. The identifier to scope the item selection
    # in the case the identifier is duplicated (e.g. replication)
    # If domain cid is present, the aggroot is select by:
    # _iid = scope internal identifier (i.e. item identifier), _sid = domain scoping id
    domain_sid  = field(type=nullable(UUID_TYPE), factory=identifier_factory, initial=None)
    domain_iid  = field(type=nullable(UUID_TYPE), factory=identifier_factory, initial=None)

    src_cmd = field(type=UUID_TYPE, factory=identifier_factory)
    domain = field(mandatory=True)
    context = field(type=UUID_TYPE, factory=identifier_factory)
    data = field(type=nullable(dict))
    code = field(type=int)
    message = field(type=str)
    msgtype = field(type=ActivityType)
    msglabel = field(type=str)



__all__ = ("ActivityLog",)
