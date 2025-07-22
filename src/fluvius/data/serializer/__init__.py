import json
from .json_encoder import FluviusJSONEncoder
from fluvius.data.data_model import DataModel, BlankModel
from pyrsistent import PClass
from fluvius.data.helper import serialize_mapping
from sqlalchemy.types import TypeDecorator, TEXT
from sqlalchemy.dialects.postgresql import JSONB


def convert_to_json_compatible(value, encoder_cls=FluviusJSONEncoder):
    encoder = encoder_cls()

    def _convert(val):
        if isinstance(val, (str, int, float, bool, type(None))):
            return val

        if isinstance(val, list):
            return [_convert(v) for v in val]

        if isinstance(val, dict):
            return {k: _convert(v) for k, v in val.items()}

        if callable(val):
            return val.__name__

        return _convert(encoder.default(val))

    return _convert(value)

class FluviusJSONField(TypeDecorator):
    impl = JSONB  # or TEXT if you want to store as string
    cache_ok = True  # Safe to use in SQLAlchemy cache

    def process_bind_param(self, value, dialect):
        # Called when saving to DB
        if value is None:
            return None

        return convert_to_json_compatible(value)

    def process_result_value(self, value, dialect):
        # Called when loading from DB
        if value is None:
            return None
        return value


def serialize_json(data: dict, cls=FluviusJSONEncoder, **kwargs) -> str:
    return json.dumps(data, cls=cls, **kwargs)


def deserialize_json(data_str) -> dict:
    return json.loads(data_str)

