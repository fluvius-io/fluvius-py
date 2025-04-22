from types import SimpleNamespace
from fluvius.data import UUID_GENR, UUID_TYPE, nullable, identifier_factory, field, DataModel
from .record import DomainEntityRecord


class MessageBundle(DomainEntityRecord):
    aggroot = field()
    message = field(str)
    src_cmd = field(type=UUID_TYPE, factory=identifier_factory)
    domain = field(mandatory=True)
    data = field(type=nullable(dict))
    recipients = field(nullable(list))
    flags = field(nullable(list))


class MessageMeta(DataModel):
    key: str = None
    name: str = None
    resources: str
    tags: list[str]


class Message(object):
    Meta = SimpleNamespace()
    Payload = SimpleNamespace

    def __init_subclass__(cls):
        cls.Meta = MessageMeta(**cls.Meta.__dict__)
        if not issubclass(cls.Payload, (DataModel, SimpleNamespace)):
            raise ValueError(f'Invalid Command Payload: {cls.Payload}')


__all__ = ("MessageBundle",)
