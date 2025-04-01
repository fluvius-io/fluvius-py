import asyncpg
import json
import sanic
from sanic.response import HTTPResponse
from sanic.response import json as json_resp

from fluvius.sanic.serializer.json_encoder import SanicJSONEncoder


class PosgreSQLJSONEncoder(SanicJSONEncoder):
    def default(self, obj):
        if isinstance(obj, sanic.compat.Header):
            return dict(obj)

        if isinstance(obj, asyncpg.Record):
            return dict(obj)

        return super(PosgreSQLJSONEncoder, self).default(obj)


def serialize(data: dict) -> str:
    return json.dumps(data, cls=PosgreSQLJSONEncoder)


def serialize_resp(data: dict, *args, **kwargs) -> HTTPResponse:
    return json_resp(data, dumps=serialize, *args, **kwargs)
