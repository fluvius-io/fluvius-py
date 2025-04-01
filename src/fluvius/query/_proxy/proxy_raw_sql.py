import asyncpg
import sanic
import json
from sanic.response import HTTPResponse
from sanic.response import json as json_resp
from fluvius.sanic.serializer.json_encoder import SanicJSONEncoder
from fluvius_query import logger, config


class PosgreSQLJSONEncoder(SanicJSONEncoder):
    def default(self, obj):
        if isinstance(obj, sanic.compat.Header):
            return dict(obj)

        if isinstance(obj, asyncpg.Record):
            return dict(obj)

        return super(PosgreSQLJSONEncoder, self).default(obj)


def serialize(data: dict) -> str:
    return json.dumps(data, cls=PosgreSQLJSONEncoder)


def serialize_response(data: dict, *args, **kwargs) -> HTTPResponse:
    return json_resp(data, dumps=serialize, *args, **kwargs)


async def delegate(
    api_prefix: str, uri: str, params: dict, headers: dict = None, resp_headers: dict = None, request=None
):
    sql = params["raw_sql"]
    dbpool = request.app.config["pool"]
    config.DEBUG_QUERY and logger.info("/fetch_sql/ Executing SQL: %s", sql)
    async with dbpool.acquire() as conn:
        response = await conn.fetch(sql)
    force_object = params["force_object"]
    if force_object:
        return serialize_response(response[0])
    return serialize_response(response)
