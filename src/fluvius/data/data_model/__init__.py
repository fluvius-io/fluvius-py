from types import SimpleNamespace
from typing import Any
from pydantic import BaseModel, Field, PrivateAttr, ConfigDict


def _create(cls, data=None, defaults=None, **kwargs):
    """
    Construct a new data model object from mutiple sources
    (dict, keyword args, other models, etc.)
    and allow setting default values.
    """

    base = {**defaults} if defaults else {}

    if isinstance(data, dict):
        base.update(data)
    elif isinstance(data, (BlankModel, type)):
        base.update(data.__dict__)
    elif isinstance(data, BaseModel):
        base.update(data.model_dump())
    elif data is not None:
        raise ValueError(f'Unable to extract data from object: {data}')

    # Fall through to this
    base.update(kwargs)
    return cls(**base)


class DataModel(BaseModel):
    """
    Pydantic BaseModel with custom defaults:
    - frozen = True
    - model_dump(by_alias=True)
    - `set` method to update and create a new instance.
    - `create` method to construct a new instance from multiple sources
    """

    model_config = ConfigDict(
        frozen=True,
        exclude_none=True,
        by_alias=True
    )

    create = classmethod(_create)

    def set(self, **kwargs):
        return self.model_copy(update=kwargs)


    def serialize(self, **kwargs):
        return self.model_dump(**kwargs)


class BlankModel(SimpleNamespace):
    create = classmethod(_create)

    def set(self, **kwargs):
        return object.replace(self, **kwargs)

    def serialize(self):
        return self.__dict__
