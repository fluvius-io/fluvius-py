from .datadef import UUID_GENR, nullable, field, serialize_mapping
from .record import DomainEntityRecord


class DomainResponse(DomainEntityRecord):
    _domain = 'response'

    kind = field()
    data = field(type=nullable(dict), factory=serialize_mapping)
    src_cmd = field()
    transact = field()

    @classmethod
    def defaults(cls):
        return dict(_id=UUID_GENR())


__all__ = ("DomainResponse",)
