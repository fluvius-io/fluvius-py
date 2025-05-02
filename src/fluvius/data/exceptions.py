from fluvius.error import (  # noqa
    NotFoundError,
    UnprocessableError
)


class StateCommittedError(UnprocessableError):
    pass


class ItemNotFoundError(NotFoundError):
    pass


class NoItemModifiedError(NotFoundError):
    pass
