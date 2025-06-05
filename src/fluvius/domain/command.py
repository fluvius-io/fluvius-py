from typing import Optional, Dict, List, Annotated, Any, Union
from fluvius.data import UUID_TYPE, UUID_GENR, identifier_factory, nullable, field, DataModel, Field, BlankModel

from .aggregate import AggregateRoot
from .entity import CommandState, DOMAIN_ENTITY_MARKER, DomainEntity
from .record import DomainEntityRecord



def model_factory(data: Any) -> Union[BlankModel, DataModel]:
    if isinstance(data, dict):
        return BlankModel(**data)

    if isinstance(data, (BlankModel, DataModel)):
        return data

    raise ValueError('Invalid payload data')


class CommandBundle(DomainEntityRecord):
    domain      = field(type=str, mandatory=True)
    command     = field(type=str, mandatory=True)
    revision    = field(type=int, mandatory=True)
    resource    = field(type=str, mandatory=True)
    identifier  = field(type=UUID_TYPE, mandatory=True, factory=identifier_factory)
    payload     = field(type=nullable(DataModel, BlankModel), mandatory=True, factory=model_factory)

    # Domain closure ID. The identifier to scope the item selection
    # in the case the identifier is duplicated (e.g. replication)
    # If domain sid is present, the aggroot is select by:
    # _iid = scope internal identifier (i.e. item identifier),
    # _sid = domain scoping id
    # See: docs/NOTES.md
    domain_sid  = field(type=nullable(UUID_TYPE), factory=identifier_factory, initial=None)
    domain_iid  = field(type=nullable(UUID_TYPE), factory=identifier_factory, initial=None)

    context     = field(type=nullable(UUID_TYPE), factory=identifier_factory, initial=None)
    status      = field(type=CommandState, mandatory=True, initial=CommandState.CREATED)


class CommandMeta(DataModel):
    key: Optional[str] = None
    name: Optional[str] = None
    desc: Optional[str] = None
    tags: Optional[List[str]] = None
    resources: Optional[tuple[str]] = None
    tags: List[str] = []
    scope_required: Optional[Dict] = None
    scope_optional: Optional[Dict] = None
    new_resource: bool = False
    auth_required: bool = True
    resource_desc: Optional[str] = None


class Command(DomainEntity):
    __meta_schema__ = CommandMeta
    __abstract__ = True

    class Meta(DomainEntity.Meta):
        pass

    def __init__(self, cmd_data):
        self._data = cmd_data


    @property
    def domain(self):
        return self._data.domain

    @property
    def revision(self):
        return self._data.revision


__all__ = ("Command",)
