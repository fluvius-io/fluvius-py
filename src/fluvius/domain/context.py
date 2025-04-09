import enum
import warnings
from datetime import datetime
from fluvius.data.helper import timestamp

from .datadef import nullable, identifier_factory, UUID_TYPE, field
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
    RABITTMQ = 'RABITTMQ'
    COMMAND_LINE = 'CLI'


def none_serializer(obj, value):
    return None


class DomainContext(DomainEntityRecord):
    domain = field(type=str, mandatory=True)
    revision = field(type=int, mandatory=True)
    transport = field(type=DomainTransport,
                      factory=DomainTransport,
                      mandatory=True)
    source = field(type=(str, type(None)), initial=lambda: None)
    timestamp = field(type=datetime, initial=timestamp)
    headers = field(type=dict, initial=dict)
    user_id = field(type=nullable(UUID_TYPE), factory=identifier_factory, initial=None)
    realm_id = field(type=nullable(UUID_TYPE), factory=identifier_factory, initial=None)
    dataset_id = field(type=nullable(UUID_TYPE), factory=identifier_factory, initial=None)
