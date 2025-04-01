from .datadef import (DomainDataModel, serialize_mapping, UUID_TYPE, UUID_GENR, field)
from .entity import CQRS_ENTITY_MARKER

from . import config

NONE_TYPE = type(None)


class DomainEntityRecord(DomainDataModel):
    _id = field(type=UUID_TYPE, initial=UUID_GENR)

    # def serialize(self):
    #     key, kind, namespace = getattr(self.__class__, CQRS_ENTITY_MARKER)
    #     data = super().serialize()
    #     data.update(_domain=key, _kind=kind, _vers=self._version)
    #     return data


class PayloadData(DomainDataModel):
    def __init_subclass__(cls):
        cls._nullable_fields = tuple(
            name
            for name, field_def in cls._pclass_fields.items()
            if NONE_TYPE in field_def.type
        )

    @classmethod
    def create(cls, kwargs):
        kwargs = serialize_mapping(kwargs)
        kwargs = {k: v for k, v in kwargs.items() if not (v is None and k not in cls._nullable_fields)}

        return super().create(kwargs, ignore_extra=config.IGNORE_COMMAND_EXTRA_FIELDS)
