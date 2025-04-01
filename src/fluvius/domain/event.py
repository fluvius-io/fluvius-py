from .datadef import ResourceReference, UUID_GENR, UUID_TYPE, identifier_factory, field, nullable
from .record import DomainEntityRecord


class Event(DomainEntityRecord):
    name     = field(type=str)
    src_cmd  = field(type=UUID_TYPE, factory=identifier_factory)
    args     = field(type=dict)
    data     = field(type=nullable(dict))
    route_id = field(type=UUID_TYPE)
    selector = field(type=UUID_TYPE)

    @classmethod
    def defaults(cls):
        return dict(_id=UUID_GENR())


__all__ = ("Event", )
