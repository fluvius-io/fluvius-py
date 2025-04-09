import asyncpg
from fluvius.error import UnprocessableError, sanic_error_handler
from sanic.request import Request
from sanic.response import json
from fluvius_query import logger, config
from .serializer import serialize_resp


async def fetch_sql(app, sql):
    dbpool = app.config["pool"]
    config.DEBUG_QUERY and logger.info("/fetch_sql/ Executing SQL: %s", sql)
    async with dbpool.acquire() as conn:
        try:
            response = await conn.fetch(sql)
            return response
        except asyncpg.exceptions.PostgresSyntaxError as e:
            raise UnprocessableError(
                errcode=422426,
                message=e.message
            )


def make_exception_response(e):
    return json(
        {"message": e.message, "code": e.code, "data": e.data},
        status=e.status_code,
    )


def sql_handler(app, force_object=False):
    def _decorator(func):
        @sanic_error_handler
        async def wrapped_func(request: Request, user, *args, **kwargs):
            base_sql = await func(request, user, *args, **kwargs)
            response = await fetch_sql(app, base_sql)
            if force_object is True:
                return serialize_resp(response[0])

            return serialize_resp(response)

        return wrapped_func

    return _decorator
