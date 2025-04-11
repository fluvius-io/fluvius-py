from pyrsistent import PClass, field, pvector_field
from fluvius.domain.aggregate import AggregateRoot
from fluvius.domain.context import DomainContext
from fluvius.data.helper import identifier_factory, nullable
from fluvius.data import UUID_GENR, UUID_TYPE

def pclass_factory(cls):
    def _factory(value):
        if value is None:
            return cls()

        if isinstance(value, cls):
            return value

        return cls(**value)

    return _factory

class WorkerRequestRelation(PClass):
    label = field(str)
    attrs = field(dict, initial=dict)
    resource = field(str)
    identifier = field(UUID_TYPE)
    domain_sid = field(type=nullable(UUID_TYPE), initial=None)
    domain_iid = field(type=nullable(UUID_TYPE), initial=None)


class WorkerContext(PClass):
    user = field(type=dict, initial=dict)
    source = field(type=nullable(str), initial=None)
    realm = field(type=dict, initial=dict)
    domain = field(nullable(str), initial=None)
    revision = field(int, initial=0)


class DomainWorkerCommand(PClass):
    command = field(str)
    resource = field(str)
    identifier = field(type=UUID_TYPE, factory=identifier_factory, initial=UUID_GENR)
    domain_sid = field(type=nullable(UUID_TYPE), initial=None)
    domain_iid = field(type=nullable(UUID_TYPE), initial=None)
    payload = field(dict, initial=dict)


def command_factory(data):
    if isinstance(data, dict):
        return DomainWorkerCommand(**data)

    if isinstance(data, DomainWorkerCommand):
        return data

    raise ValueError(f'Invalid CQRS command spec: {data}')


def command_list_factory(data):
    if isinstance(data, (list, tuple)):
        return tuple(command_factory(item) for item in data)

    return (command_factory(data), )


class DomainWorkerRequest(PClass):
    context = field(WorkerContext, factory=pclass_factory(WorkerContext))
    command = field(DomainWorkerCommand, factory=pclass_factory(DomainWorkerCommand))
    headers = field(type=dict, initial=dict)
    relation = field(nullable(WorkerRequestRelation), initial=None)


class BatchDomainWorkerRequest(DomainWorkerRequest):
    command = field(tuple, factory=command_list_factory, mandatory=True)

