from pydantic import Field as PydanticField
from fluvius.query import logger

def QueryField(
    title,
    preset="string",        # Query operators preset, define the list of query operators available for the field
    identifier=None,        # Whether the field is the identifier field of the resource. Only one identifier allowed for 1 resource.
    sortable=True,          # Field is sortable
    source=None,            # Source field name. The name of the field in the underlying table.
    default_filter=None,    # Default filter operator for the field.
    weight=0,               # Ordering weight for the field
    array=False,
    dtype=None,
    enum=None,
    enum_values=None,
    excluded=False,
    ftype=None,
    finput=None,
    hidden=False,
    item_type=None,         # Unused, to be removed.
    json_schema_extra=None,
    **kwargs
):
    extra = (json_schema_extra or {}) | dict(
        preset=preset,
        identifier=identifier,
        sortable=sortable,
        source=source,
        default_filter=default_filter,
        weight=weight,
        array=array,
        dtype=dtype,
        enum=str(enum) if enum else None,
        enum_values=enum_values,
        excluded=excluded,
        ftype=ftype,
        finput=finput,
        hidden=hidden,
    )

    return PydanticField(title=title, json_schema_extra=extra, **kwargs)


def ExcludedField(title="Excluded", preset=None, excluded=True, sortable=False, identifier=None, hidden=True, **kwargs):
    return QueryField(title=title, preset="none", excluded=True, **kwargs)


def StringField(title, **kwargs):
    return QueryField(title=title, preset="string", **kwargs)


def FloatField(title, **kwargs):
    return QueryField(title=title, preset="number", **kwargs)


def PrimaryID(title="ID", weight=100, **kwargs):
    return QueryField(title=title, preset="uuid", source="_id", weight=weight, identifier=True, hidden=True, **kwargs)


def UUIDField(title, **kwargs):
    return QueryField(title=title, preset="uuid", **kwargs)


def TextSearchField(title, **kwargs):
    return QueryField(title=title, preset="textsearch", **kwargs)


def BooleanField(title, **kwargs):
    return QueryField(title=title, preset="boolean", **kwargs)


def EnumField(title, ftype="enum", **kwargs):
    return QueryField(title=title, preset="enum", ftype=ftype, **kwargs)


def DateField(title, **kwargs):
    return QueryField(title=title, preset="date", **kwargs)


def DatetimeField(title, **kwargs):
    return QueryField(title=title, preset="datetime", **kwargs)


def ArrayField(title, **kwargs):
    return QueryField(title=title, preset="array", **kwargs)


def JSONField(title, **kwargs):
    return QueryField(title=title, preset="json", **kwargs)


def IntegerField(title, **kwargs):
    return QueryField(title=title, preset="integer", **kwargs)


def NumberField(title, **kwargs):
    return QueryField(title=title, preset="number", **kwargs)


def DictField(title, **kwargs):
    return QueryField(title=title, preset="none", **kwargs)


def ListField(title, **kwargs):
    return QueryField(title=title, preset="none", **kwargs)
