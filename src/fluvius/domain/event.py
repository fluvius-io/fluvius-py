from fluvius.data import UUID_GENR, UUID_TYPE, identifier_factory, field, nullable, BlankModel, DataModel
from .record import DomainEntityRecord
from .entity import DomainEntity


class EventRecord(DomainEntityRecord):
    event     = field(type=str)
    src_cmd   = field(type=UUID_TYPE, factory=identifier_factory)
    args      = field(type=dict)
    data      = field(type=nullable(dict, BlankModel, DataModel))


class Event(DomainEntity):
    pass

__all__ = ("Event", )
