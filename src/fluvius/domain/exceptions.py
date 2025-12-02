from fluvius.error import BadRequestError, InternalServerError


class DomainEntityError(BadRequestError):
    """Domain entity validation error"""
    errcode = "D00.001"


class DomainEventValidationError(BadRequestError):
    """Domain event validation error"""
    errcode = "D00.002"


class DomainCommandValidationError(BadRequestError):
    """Domain command validation error"""
    errcode = "D00.003"


class CommandProcessingError(InternalServerError):
    """Command processing error"""
    errcode = "D00.004"


class EventReceivingError(InternalServerError):
    """Event receiving error"""
    errcode = "D00.005"
