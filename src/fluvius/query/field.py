from pydantic import Field as PydanticField
from fluvius.query import logger

def QueryField(title, preset="string", identifier=None, sortable=True, source=None, json_schema_extra=None, default_filter=None, hidden=False, **kwargs):
    extra = (json_schema_extra or {}) | dict(
        preset=preset,
        sortable=sortable,
        identifier=identifier,
        default_filter=default_filter,
        hidden=hidden,
    )

    return PydanticField(title=title, json_schema_extra=extra, alias=source, **kwargs)


def StringField(title, **kwargs):
    return QueryField(title=title, preset="string", **kwargs)


def PrimaryID(title, identifier=True, **kwargs):
    return QueryField(title=title, preset="uuid", source="_id", identifier=identifier, hidden=True, **kwargs)


def UUIDField(title, **kwargs):
    return QueryField(title=title, preset="uuid", **kwargs)

