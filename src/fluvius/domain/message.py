from types import SimpleNamespace
from fluvius.data import UUID_GENR, UUID_TYPE, nullable, identifier_factory, field, DataModel, BlankModel
from .record import DomainEntityRecord
from .entity import DomainEntity


class MessageRecord(DomainEntityRecord):
    aggroot = field()
    message = field(str)
    src_cmd = field(type=UUID_TYPE, factory=identifier_factory)
    domain = field(mandatory=True)
    data = field(type=nullable(dict, DataModel, BlankModel))
    recipients = field(nullable(list))
    flags = field(nullable(list))


class MessageMeta(DataModel):
    key: str = None
    name: str = None
    tags: list[str] = tuple()


class Message(DomainEntity):
    __meta_schema__ = MessageMeta
    __abstract__ = True



__all__ = ("MessageRecord",)
