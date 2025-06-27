from fluvius import config, logger


DEBUG_APP_EXCEPTION = config.DEBUG_APP_EXCEPTION


class FluviusException(Exception):
    status_code = 500
    label = "Internal Error"
    errcode = "A00-000"

    def __init__(self, errcode, message, payload=None):
        self.message = message
        self.payload = payload
        self.errcode = errcode

        DEBUG_APP_EXCEPTION and logger.exception(message)

    def __str__(self):
        if self.payload is None:
            return f"{self.errcode} [{self.status_code}] >> {self.message}"

        return f"{self.errcode} [{self.status_code}] >> {self.message} >> {self.payload}"

    @property
    def content(self):
        if not self.payload:
            return {"errcode": self.errcode, "message": self.message}

        return {"errcode": self.errcode, "message": self.message, "payload": self.payload}


class NotFoundError(FluviusException):
    label = "Not Found"
    status_code = 404
    errcode = "A00404"


class PreconditionFailedError(FluviusException):
    label = "Precondition Failed"
    status_code = 412
    errcode = "A00412"


class BadRequestError(FluviusException):
    label = "Bad Request"
    status_code = 400
    errcode = "A00400"


class UnauthorizedError(FluviusException):
    label = "Unauthorized Request"
    status_code = 401
    errcode = "A00401"


class ForbiddenError(FluviusException):
    label = "Forbidden"
    status_code = 403
    errcode = "A00403"


class UnprocessableError(FluviusException):
    label = "Unprocessable Entity"
    status_code = 422
    errcode = "A00422"


class LockedError(FluviusException):
    label = "Resource Locked"
    status_code = 423
    errcode = "A00423"


class InternalServerError(FluviusException):
    label = "Internal Server Error"
    status_code = 500
    errcode = "A00500"


class AssertionFailed(BadRequestError):
    label = "Assertion Failed"
    errcode = "A00401"
