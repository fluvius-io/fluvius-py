from fluvius.exceptions import (  # noqa
    NotFoundError,
    InternalServerError,
    UnprocessableError
)


class StateCommittedError(InternalServerError):
    pass


class ItemNotFoundError(NotFoundError):
    pass


class NoItemModifiedError(NotFoundError):
    pass
