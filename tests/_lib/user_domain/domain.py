from fluvius.domain import Domain, SQLDomainLogStore

from .aggregate import UserAggregate
from .state import UserStateManager

class UserDomain(Domain):
    __namespace__   = 'user-profile'
    __aggregate__   = UserAggregate
    __statemgr__    = UserStateManager
    __logstore__    = SQLDomainLogStore


class UserResponse(UserDomain.Response):
    pass


class UserMessage(UserDomain.Message):
    pass
