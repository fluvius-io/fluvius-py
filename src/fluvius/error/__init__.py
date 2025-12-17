from fluvius import config, logger
from .tracker import ErrorTracker


DEBUG_APP_EXCEPTION = config.DEBUG_APP_EXCEPTION


class FluviusException(Exception):
    status_code = 500
    label = "Internal Error"
    errcode = "A00.000"

    def __init__(self, errcode, message, details=None):
        self.message = message
        self.details = details
        self.errcode = errcode

        DEBUG_APP_EXCEPTION and logger.exception(message)

    def __str__(self):
        if self.details is None:
            return f"{self.errcode} [{self.status_code}] >> {self.message}"

        return f"{self.errcode} [{self.status_code}] >> {self.message} >> {self.details}"

    @property
    def content(self):
        if not self.details:
            return {"errcode": self.errcode, "message": self.message}

        return {"errcode": self.errcode, "message": self.message, "details": self.details}


class NotFoundError(FluviusException):
    label = "Not Found"
    status_code = 404
    errcode = "A00.404"


class PreconditionFailedError(FluviusException):
    label = "Precondition Failed"
    status_code = 412
    errcode = "A00.412"


class BadRequestError(FluviusException):
    label = "Bad Request"
    status_code = 400
    errcode = "APP00.400"


class UnauthorizedError(FluviusException):
    label = "Unauthorized Request"
    status_code = 401
    errcode = "A00.401"


class ForbiddenError(FluviusException):
    label = "Forbidden"
    status_code = 403
    errcode = "A00.403"


class UnprocessableError(FluviusException):
    label = "Unprocessable Entity"
    status_code = 422
    errcode = "A00.422"


class LockedError(FluviusException):
    label = "Resource Locked"
    status_code = 423
    errcode = "A00.423"


class InternalServerError(FluviusException):
    label = "Internal Server Error"
    status_code = 500
    errcode = "A00.500"


class AssertionFailed(BadRequestError):
    label = "Assertion Failed"
    errcode = "APP00.400"
