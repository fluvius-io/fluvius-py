class DomainEntityError(ValueError):
    pass


class DomainEventValidationError(ValueError):
    pass


class DomainCommandValidationError(ValueError):
    pass


class CommandProcessingError(Exception):
    pass


class EventReceivingError(Exception):
    pass
