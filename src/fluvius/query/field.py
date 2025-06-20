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
    json_schema_extra=None,
    **kwargs
):
    extra = (json_schema_extra or {}) | dict(
        preset=preset,
        sortable=sortable,
        identifier=identifier,
        default_filter=default_filter,
        hidden=hidden,
        array=array,
        enum=str(enum) if enum else None,
        weight=weight,
        source=source
    )

    return PydanticField(title=title, json_schema_extra=extra, **kwargs)


def StringField(title, **kwargs):
    return QueryField(title=title, preset="string", **kwargs)


def FloatField(title, **kwargs):
    return QueryField(title=title, preset="string", **kwargs)


def PrimaryID(title, weight=100, **kwargs):
    return QueryField(title=title, preset="uuid", source="_id", weight=weight, identifier=True, hidden=True, **kwargs)


def UUIDField(title, **kwargs):
    return QueryField(title=title, preset="uuid", **kwargs)


def TextSearchField(title, **kwargs):
    return QueryField(title=title, preset="textsearch", **kwargs)


def BooleanField(title, **kwargs):
    return QueryField(title=title, preset="string", **kwargs)


def EnumField(title, **kwargs):
    return QueryField(title=title, preset="string", **kwargs)


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

