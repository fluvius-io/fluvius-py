from typing import Optional
from fluvius.data import UUID_TYPE, nullable, field, serialize_mapping, identifier_factory, DataModel, BlankModel
from .record import DomainEntityRecord
from .entity import DomainEntity


class ResponseRecord(DomainEntityRecord):
    response = field(str)
    src_cmd = field(type=UUID_TYPE, factory=identifier_factory)
    data = field(type=dict, factory=serialize_mapping)


class ResponseMeta(DataModel):
    key: Optional[str] = None
    name: Optional[str] = None
    tags: list[str] = tuple()


class DomainResponse(DomainEntity):
    __meta_schema__ = ResponseMeta
    __abstract__ = True

    # Response may accept any data by default
    # since the data is generated from server.
    class Data(BlankModel):
        pass


__all__ = ("DomainResponse",)
