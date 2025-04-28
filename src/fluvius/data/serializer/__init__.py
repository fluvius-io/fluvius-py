import json
from .json_encoder import FluviusJSONEncoder
from fluvius.data.data_model import DataModel, BlankModel
from pyrsistent import PClass


def serialize_json(data: dict, cls=FluviusJSONEncoder, **kwargs) -> str:
    return json.dumps(data, cls=cls, **kwargs)


def deserialize_json(data_str) -> dict:
    return json.loads(data_str)


def serialize_mapping(data, **kwargs):
    if data is None:
        return {}

    if isinstance(data, dict):
        return data

    if isinstance(data, DataModel):
        return data.model_dump()

    if isinstance(data, BlankModel):
        return data.__dict__

    if isinstance(data, PClass):
        return data.serialize()

    raise ValueError('Unable to serialize value to mapping: %s' % str(data))
