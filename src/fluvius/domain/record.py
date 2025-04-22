from fluvius.data import (PClass, serialize_mapping, UUID_TYPE, UUID_GENR, field)
from .entity import DOMAIN_ENTITY_MARKER

from . import config

NONE_TYPE = type(None)


class DomainEntityRecord(PClass):
    _id = field(type=UUID_TYPE, initial=UUID_GENR)
