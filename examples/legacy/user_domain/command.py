from fluvius.domain.record import field
from fluvius.domain.command import Command
from fluvius.domain.response import DomainResponse
from .domain import UserDomain


class UserCommand(Command):
    resource = 'app-user'

    @property
    def user_id(self):
        return self.aggroot.identifier


@UserDomain.entity
class ActivateUser(UserCommand):
    pass


@UserDomain.entity
class ExecuteUserAction(UserCommand):
    actions = field(type=list, mandatory=True)


@UserDomain.entity
class RemoveTOTP(UserCommand):
    pass


@UserDomain.entity
class DeactivateUser(UserCommand):
    pass


@UserDomain.entity
class ReconcileUser(UserCommand):
    pass


@UserDomain.entity
class UserResponse(DomainResponse):
    data = field(type=str)


@UserDomain.command_processor(ExecuteUserAction)
async def handle__execute_user_action(aggproxy, cmd):
    yield await aggproxy.execute_actions(cmd.user_id, cmd.actions)
    yield aggproxy.create_response('user-response', cmd, data='execute-actions')


@UserDomain.command_processor(ActivateUser)
async def handle__activate_user(aggproxy, cmd):
    actions = ["terms_and_conditions", "VERIFY_EMAIL", "UPDATE_PASSWORD"]
    yield await aggproxy.execute_actions(cmd.user_id, actions)
    yield aggproxy.create_response('user-response', cmd, data='user-activated')


@UserDomain.command_processor(DeactivateUser)
async def handle__deactivate_user(aggproxy, cmd):
    yield await aggproxy.deactivate(cmd.user_id)
    yield aggproxy.create_response('user-response', cmd, data='user-deactivated')


@UserDomain.command_processor(ReconcileUser)
async def handle__reconcile(aggproxy, cmd):
    yield await aggproxy.reconcile(cmd.user_id)
    yield aggproxy.create_response('user-response', cmd, data='user-reconciled')


@UserDomain.command_processor(RemoveTOTP)
async def handle__remove_totp(aggproxy, cmd):
    yield await aggproxy.remove_totp(cmd.user_id)
    yield aggproxy.create_response('user-response', cmd, data='remove-totp')
