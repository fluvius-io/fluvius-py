import json
from .json_encoder import FluviusJSONEncoder
from fluvius.data.data_model import DataModel, BlankModel
from pyrsistent import PClass
from fluvius.data.helper import serialize_mapping


def serialize_json(data: dict, cls=FluviusJSONEncoder, **kwargs) -> str:
    return json.dumps(data, cls=cls, **kwargs)


def deserialize_json(data_str) -> dict:
    return json.loads(data_str)

