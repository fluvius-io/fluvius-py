import uuid
from types import SimpleNamespace
from dataclasses import is_dataclass, asdict

from base64 import encodebytes
from datetime import datetime, date
from enum import Enum, IntEnum
from json.encoder import JSONEncoder
from pyrsistent import PClass, PRecord
from fluvius.data import logger
from fluvius.data.data_driver.sqla.schema import SqlaDataSchema
from fluvius.data.data_model import DataModel, BlankModel

from fluvius.helper.timeutil import datetime_to_str

DATE_FORMAT = '%Y-%m-%d'
BYTES_DECODER = 'utf_8'


class FluviusJSONEncoder(JSONEncoder):
    ''' Sample usage:

        from fluvius.domain.serializer.json_encoder import FluviusJSONEncoder
        from sanic.response import json

        ....
        return json(data, cls=FluviusJSONEncoder)
    '''

    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)

        if isinstance(obj, (PClass, PRecord)):
            return obj.serialize()

        if isinstance(obj, SqlaDataSchema):
            return obj.serialize()

        if isinstance(obj, SimpleNamespace):
            return obj.__dict__

        if isinstance(obj, DataModel):
            return obj.model_dump()

        if is_dataclass(obj):
            return asdict(obj)

        if isinstance(obj, datetime):
            return datetime_to_str(obj)

        if isinstance(obj, (set, tuple)):
            return list(obj)

        if isinstance(obj, (Enum, IntEnum)):
            return obj.value

        if isinstance(obj, date):
            # @TODO: Proper format date in a configurable manner
            return obj.strftime(DATE_FORMAT)

        if isinstance(obj, bytes):
            # @TODO: Clarify the use case here.
            return encodebytes(obj).decode(BYTES_DECODER)
        
        if callable(obj):
            return obj.__name__

        return super(FluviusJSONEncoder, self).default(obj)
