from functools import wraps
from typing import Union
from sanic import response
from fluvius.exceptions import DEBUG_APP_EXCEPTION, AppException
from pyrsistent import InvariantException

from . import logger


def make_exception_response(e: Union[AppException, InvariantException]):
    if DEBUG_APP_EXCEPTION:
        logger.exception(e)

    if isinstance(e, AppException):
        resp = {
            "message": e.message, "code": e.code, "data": e.data,
            "_status": "ERROR"
        }
        status = e.status_code
    elif isinstance(e, InvariantException):
        missing_fields = [field.partition(".")[-1] for field in e.missing_fields]

        resp = {
            "message": str(e), "code": 400783,
            "invariant_errors": e.invariant_errors,
            "missing_fields": missing_fields,
            "_status": "ERROR"
        }
        status = 400

    return response.json(resp, status=status)


def sanic_error_handler(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except (AppException, InvariantException) as e:
            return make_exception_response(e)
        except Exception as e:
            logger.exception(
                "Un-expected error at [%s].\n[args] = %s\n[kwargs] = %s",
                func, args, kwargs
            )
            return response.json({"message": str(e), "code": 500382}, status=500)

    return wrapper
