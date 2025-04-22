from datetime import datetime
from fluvius.data import PClass, field, UUID_GENR, UUID_TYPE, timestamp, nullable

class ImmutableDomainResource(PClass):
    _id      = field(type=UUID_TYPE, initial=UUID_GENR)
    _created = field(datetime, mandatory=True, initial=timestamp)
    _updated = field(datetime, mandatory=True, initial=timestamp)
    _creator = field(nullable(UUID_TYPE))
    _updater = field(nullable(UUID_TYPE))
    _deleted = field(nullable(datetime))
    _etag    = field(nullable(str), mandatory=True, initial=None)
