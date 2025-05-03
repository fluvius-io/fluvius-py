import enum
import warnings
from datetime import datetime
from fluvius.data.helper import timestamp

from fluvius.data import nullable, identifier_factory, UUID_TYPE, field
from .record import DomainEntityRecord


class DomainServiceProxy(object):
    ''' To filter the functionaly that will be exposed to CQRS handlers '''

    def __init__(self, *args, **kwargs):
        pass

    @property
    def mqtt_client(self):
        return self._mqtt_client

    @property
    def arq_client(self):
        return self._arq_client

    @property
    def lightq(self):
        return self._lightq

    @property
    def brokerage_client(self):
        return self._brokerage_client


class DomainTransport(enum.Enum):
    SANIC = 'SANIC'
    REDIS = 'REDIS'
    KAFKA = 'KAFKA'
    FASTAPI = 'FASTAPI'
    RABITTMQ = 'RABITTMQ'
    COMMAND_LINE = 'CLI'
    UNKNOWN = 'UNKNOWN'


class DomainContext(DomainEntityRecord):
    domain = field(type=str, initial=lambda: '<no-name>')
    revision = field(type=int, initial=lambda: 0)
    transport = field(type=DomainTransport,
                      factory=DomainTransport,
                      initial=lambda: DomainTransport.UNKNOWN,
                      mandatory=True)
    # serial = field(type=int, mandatory=True, initial=lambda: 0)
    source = field(type=(str, type(None)), initial=lambda: None)
    timestamp = field(type=datetime, initial=timestamp)
    headers = field(type=dict, initial=dict)
    # profile_id = field(type=nullable(UUID_TYPE), factory=identifier_factory, initial=None)
    realm_id = field(type=nullable(UUID_TYPE), factory=identifier_factory, initial=None)
    user_id = field(type=nullable(UUID_TYPE), factory=identifier_factory, initial=None)
