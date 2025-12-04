from typing import Optional, Type
from types import SimpleNamespace
from fluvius.domain import logger
from fluvius.data import UUID_GENR, UUID_TYPE, nullable, identifier_factory, field, DataModel, BlankModel
from fluvius.error import InternalServerError
from fluvius.helper import ImmutableNamespace

from .record import DomainEntityRecord
from .entity import DomainEntity


class MessageBundle(DomainEntityRecord):
    aggroot = field()
    msg_key = field(str)
    src_cmd = field(type=UUID_TYPE, factory=identifier_factory)
    domain = field(mandatory=True)
    data = field(type=(dict, DataModel, BlankModel))
    flag = field(nullable(list))


class MessageMeta(DataModel):
    key: str
    name: str
    tags: list[str] = tuple()


class Message(DomainEntity):
    __meta_schema__ = MessageMeta
    __abstract__ = True


class MessageDispatcher(object):
    __dispatch_map__ = {}
    __config__ = ImmutableNamespace

    def __init__(self, domain, app=None, **config):
        self._app = app
        self._domain = domain
        self._config = self.validate_config(config)

    def validate_config(self, config):
        config = dict(SHOW_LOG=True) | config
        return self.__config__(**{k.upper(): v for k, v in config.items()})

    def __init_subclass__(cls):
        cls.__dispatch_map__ = {}

    @property
    def app(self):
        return self._app

    @property
    def config(self):
        return self._config

    @property
    def domain(self):
        return self._domain

    @classmethod
    def register(cls, msg_cls: Type[Message]):
        if not issubclass(msg_cls, Message):
            raise InternalServerError('D00.801', f'Invalid message class: {msg_cls}')

        cls.__dispatch_map__.setdefault(msg_cls.Meta.key, tuple())

        def _decorator(func):
            cls.__dispatch_map__[msg_cls.Meta.key] += (func,)
            return func

        return _decorator


    async def dispatch(self, msg_bundle: MessageBundle):
        if not isinstance(msg_bundle, MessageBundle):
            raise InternalServerError('D00.803', f'Invalid message bundle: {msg_bundle}')

        try:
            dispatchers = self.__dispatch_map__[msg_bundle.msg_key]
        except KeyError:
            raise InternalServerError('D00.802', f'There is no message dispatcher for message of type: [{msg_bundle.msg_key}]')

        for dispatcher in dispatchers:
            await dispatcher(self, msg_bundle)



__all__ = ("MessageBundle",)
