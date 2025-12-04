from fluvius.domain import Domain, SQLDomainLogStore, MessageDispatcher, logger

from .aggregate import UserAggregate
from .state import UserStateManager

class UserDomain(Domain):
    __namespace__   = 'user-profile'
    __aggregate__   = UserAggregate
    __statemgr__    = UserStateManager
    __logstore__    = SQLDomainLogStore
    __dispatcher__  = MessageDispatcher


class UserResponse(UserDomain.Response):
    pass


class UserMessage(UserDomain.Message):
    pass


@MessageDispatcher.register(UserMessage)
async def dispatch_user_message(dispatcher, bundle):
    logger.warning(f'Dispatching message: {dispatcher} => {bundle}')
