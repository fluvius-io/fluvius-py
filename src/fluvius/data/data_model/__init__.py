from types import SimpleNamespace
from pydantic import BaseModel, Field


def _create(cls, data=None, defaults=None, **kwargs):
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
    model_config = {"frozen": True}
    create = classmethod(_create)


class BlankModel(SimpleNamespace):
    create = classmethod(_create)
