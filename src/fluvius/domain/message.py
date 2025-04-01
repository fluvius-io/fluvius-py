from .datadef import ResourceReference, UUID_GENR, UUID_TYPE, nullable, identifier_factory, field
from .record import DomainEntityRecord, PayloadData


class DomainMessage(DomainEntityRecord):
    aggroot = field()
    src_cmd = field(type=UUID_TYPE, factory=identifier_factory)
    src_evt = field(type=UUID_TYPE, factory=identifier_factory)
    domain = field(mandatory=True)
    data = field(type=nullable(dict))
    transact = field()
    recipients = field(nullable(list))
    flags = field(nullable(list))

    @classmethod
    def defaults(cls):
        return dict(_id=UUID_GENR(), domain="")


class DomainMessageData(PayloadData):
    pass


__all__ = ("DomainMessage",)
