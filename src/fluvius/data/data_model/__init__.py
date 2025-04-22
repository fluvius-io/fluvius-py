from types import SimpleNamespace
from pydantic import BaseModel, Field


def _create(cls, data=None, **kwargs):
    if isinstance(data, BlankModel):
        data = data.__dict__

    if isinstance(data, BaseModel):
        data = data.dict()

    if isinstance(data, dict):
        data = {**data, **kwargs}

    if data is None:
        data = kwargs

    return cls(**data)


class DataModel(BaseModel):
    create = classmethod(_create)


class BlankModel(SimpleNamespace):
    create = classmethod(_create)
