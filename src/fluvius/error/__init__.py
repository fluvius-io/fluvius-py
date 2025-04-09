from fluvius import config


DEBUG_APP_EXCEPTION = config.DEBUG_APP_EXCEPTION


class AppException(Exception):
    status_code = 500
    label = "Internal Error"

    def __init__(self, errcode, message, data=None):
        self.message = message
        self.code = errcode
        self.data = data

    def __repr__(self):
        # This exception is meant to be handled by the
        # application error handler.
        return "[!EXCEPTION!] " + self.__str__()

    def __unicode__(self):
        return self.__str__()

    def __str__(self):
        if self.data is None:
            return f"{self.code} [{self.status_code}] >> {self.message}"

        return f"{self.code} >> {self.message} >> {self.data}"


class ApiRequestException(AppException):
    def __init__(self, resp):
        code = resp.status_code
        try:
            data = resp.json()
        except Exception:
            data = resp.text

        try:
            msg = data["_error"]["message"]
        except KeyError:
            if isinstance(resp.text, str):
                msg = resp.text[:250] + ("..." if len(resp.text) > 250 else "")
            else:
                msg = "[No response]"

        super(ApiRequestException, self).__init__(code, msg, data)


class NotFoundError(AppException):
    label = "Not Found"
    status_code = 404


class PreconditionFailedError(AppException):
    label = "Precondition Failed"
    status_code = 412


class BadRequestError(AppException):
    label = "Bad Request"
    status_code = 400


class UnauthorizedError(AppException):
    label = "Unauthorized Request"
    status_code = 401


class ForbiddenError(AppException):
    label = "Forbidden"
    status_code = 403


class UnprocessableError(AppException):
    label = "Unprocessable Entity"
    status_code = 422


class LockedError(AppException):
    label = "Resource Locked"
    status_code = 423


class InternalServerError(AppException):
    label = "Internal Server Error"
    status_code = 500

