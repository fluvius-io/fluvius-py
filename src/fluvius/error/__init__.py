from ._meta import config, logger
from .tracker import ErrorTracker


DEVELOPER_MODE = config.DEVELOPER_MODE


class FluviusException(Exception):
    status_code = 500
    label = "Internal Error"
    tracebk = None

    def __init__(self, errcode, errmesg, errdata=None, errhint=None):
        self.errmesg = errmesg  # Error message, 1 line that describing the error.
        self.errcode = errcode  # Unique code that identify the error, must be visbily hard-coded at the error creation.
        self.errdata = errdata  # Technical data for troubleshooting the error.
        self.errhint = errhint  # User hint on how to resolve the error.

        if DEVELOPER_MODE:
            import traceback
            self.tracebk = traceback.format_exc()

            logger.exception(errmesg)

    def __str__(self):
        return f"[{self.status_code}] >CODE> {self.errcode} >MESG> {self.errmesg} >DATA> {self.errdata} >HINT> {self.errhint}"

    @property
    def content(self):
        return {
            k: v for (k, v) in (
                ("errcode", self.errcode),
                ("errmesg", self.errmesg),
                ("errdata", self.errdata),
                ("errhint", self.errhint),
                ("tracebk", self.tracebk)
            )
            if v is not None
        }


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
    errcode = "A00.400"


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
    status_code = 400
    errcode = "A00.405"
