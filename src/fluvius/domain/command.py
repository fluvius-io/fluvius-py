from typing import Optional, Dict, List, Annotated, Any
from fluvius.data import UUID_TYPE, UUID_GENR, identifier_factory, nullable, field, DataModel, Field, BlankModel

from .aggregate import AggregateRoot
from .entity import CommandState, DOMAIN_ENTITY_MARKER, DomainEntity
from .record import DomainEntityRecord
from .context import DomainContext

from pydantic import BeforeValidator

from . import config

def model_factory(data):
    if isinstance(data, dict):
        return BlankModel(**data)

    return data

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
    key: str = None
    name: str = None
    desc: str = None
    resources: tuple[str] = ('_ALL', )
    tags: list[str] = None
    fetchroot: bool = True
    endpoints: Optional[Dict] = None
    scoped: Optional[Dict] = None
    normal: bool = True
    new_resource: bool = False


class Command(DomainEntity):
    __meta_schema__ = CommandMeta
    __abstract__ = True


__all__ = ("Command",)
