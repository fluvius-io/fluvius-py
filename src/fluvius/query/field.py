from pydantic import Field as PydanticField
from fluvius.query import logger

def QueryField(
    title,
    preset="string",
    identifier=None,
    sortable=True,
    source=None,
    default_filter=None,
    weight=0,
    hidden=False,
    array=False,
    enum=None,
    excluded=False,
    finput=None,
    dtype=None,
    item_type=None,
    enum_values=None,
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
        hidden=hidden,
        array=array,
        enum=str(enum) if enum else None,
        excluded=excluded,
        finput=finput,
        dtype=dtype,
        enum_values=enum_values,
        item_type=item_type,
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


def EnumField(title, **kwargs):
    return QueryField(title=title, preset="enum", **kwargs)


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

