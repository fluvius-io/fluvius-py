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


class EventHandler(object):
    __config__ = ImmutableNamespace

    def __init__(self, domain, app=None, **config):
        self._app = app
        self._domain = domain
        self._config = self.validate_config(config)

    def validate_config(self, config, **defaults):
        config = defaults | config
        return self.__config__(**{k.upper(): v for k, v in config.items()})

    @property
    def app(self):
        return self._app

    @property
    def config(self):
        return self._config

    @property
    def domain(self):
        return self._domain

    def process_event(self, event, statemgr):
        pass


__all__ = ("Event", )
