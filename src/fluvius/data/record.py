from enum import Enum
from pyrsistent import PClass, field  # noqa
from .identifier import UUID_TYPE, identifier_factory, UUID_GENR


def _hint_fields():
    FIELD_HINTS = {}

    def _get_hint(fld):
        return FIELD_HINTS.get(fld)

    def _hinted_field(*args, hint=None, **kwargs):
        fld = field(*args, **kwargs)
        FIELD_HINTS[fld] = hint
        return fld

    return _hint_fields, _get_hint


hfield, get_hint = _hint_fields()


class BUILTIN_FIELDS(Enum):
    DOMAIN_IDENTIFIER_FIELD = '_iid'
    DOMAIN_SCOPING_FIELD = '_did'
    RECORD_IDENTIFIER_FIELD = '_id'
    RECORD_INVALIDATE_FIELD = '_deleted'
    RECORD_ETAG_FIELD    = '_etag'
    RECORD_CREATOR_FIELD = '_creator'
    RECORD_CREATED_FIELD = '_created'
    RECORD_UPDATER_FIELD = '_updater'
    RECORD_UPDATED_FIELD = '_updated'
    SCHEMA_VERSIONING_FIELD = '_version'


class DataRecord(PClass):
    _version = 0

    _id = field(type=UUID_TYPE,
                factory=identifier_factory,
                initial=UUID_GENR,
                mandatory=True)

    @classmethod
    def defaults(cls):
        return dict()

    @classmethod
    def create(
        cls, _data=None, _factory_fields=None, ignore_extra=None, **kwargs
    ):
        '''
        Factory method. Will create a new PRecord of the current type and assign the values
        specified in kwargs.
        :param ignore_extra: A boolean which when set to True will ignore any keys which appear in kwargs that are not
                             in the set of fields on the PRecord.
        '''

        item = cls.defaults()
        if _data:
            _data = _data.serialize() if isinstance(_data, PClass) else _data
            item.update(_data)

        if kwargs:
            item.update(kwargs)

        if ignore_extra:
            item = {k: item[k] for k in cls._pclass_fields if k in item}

        return cls(_factory_fields=_factory_fields, **item)


class DataElement(PClass):
    pass
