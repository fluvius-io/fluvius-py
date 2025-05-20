# from fluvius.domain.event import Event
# from fluvius.domain.record import field, PClass
# from .domain import UserDomain


# class UserEventData(PClass):
#     actions = field(type=list, mandatory=True)


# class UserEvent(Event):
#     data = field(type=UserEventData, mandatory=True)


# @UserDomain.entity('user-action-executed')
# class UserActionExecuted(UserEvent):
#     pass


# @UserDomain.entity('user-totp-removed')
# class UserTOTPRemoved(UserEvent):
#     pass


# @UserDomain.entity('user-deactivated')
# class UserDeactivated(UserEvent):
#     pass


# @UserDomain.entity('user-reconciled')
# class UserReconciled(UserEvent):
#     pass


# @UserDomain.event_committer(UserEvent)
# async def process__user_event(self, event):
#     yield None
#     # yield print('===', event)
