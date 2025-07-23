from fluvius.data import serialize_mapping, DataModel
from .domain import UserDomain
from typing import List, Optional

Command = UserDomain.Command


class ActivateUser(Command):
    """Activate a user account with required actions"""

    class Meta:
        key = 'activate-user'
        name = 'Activate User'
        resources = ("app-user",)
        tags = ["user", "activation"]
        auth_required = True
        description = "Activate user account and set required actions"

    class Data(DataModel):
        """No additional data required for activation"""
        pass

    async def _process(self, agg, stm, payload):
        actions = ["terms_and_conditions", "VERIFY_EMAIL", "UPDATE_PASSWORD"]
        result = await agg.execute_actions(self.user_id, actions)
        yield agg.create_response(serialize_mapping(result), _type="user-response")

    @property
    def user_id(self):
        return self.aggroot.identifier


class ExecuteUserAction(Command):
    """Execute specific actions for a user"""

    class Meta:
        key = 'execute-user-action'
        name = 'Execute User Action'
        resources = ("app-user",)
        tags = ["user", "action"]
        auth_required = True
        description = "Execute specified actions for user account"

    class Data(DataModel):
        actions: List[str]

    async def _process(self, agg, stm, payload):
        result = await agg.execute_actions(self.user_id, payload.actions)
        yield agg.create_response(serialize_mapping(result), _type="user-response")

    @property
    def user_id(self):
        return self.aggroot.identifier


class RemoveTOTP(Command):
    """Remove TOTP (Time-based One-Time Password) from user account"""

    class Meta:
        key = 'remove-totp'
        name = 'Remove TOTP'
        resources = ("app-user",)
        tags = ["user", "security", "totp"]
        auth_required = True
        description = "Remove TOTP authentication from user account"

    class Data(DataModel):
        """No additional data required for TOTP removal"""
        pass

    async def _process(self, agg, stm, payload):
        result = await agg.remove_totp(self.user_id)
        yield agg.create_response(serialize_mapping(result), _type="user-response")

    @property
    def user_id(self):
        return self.aggroot.identifier


class DeactivateUser(Command):
    """Deactivate a user account"""

    class Meta:
        key = 'deactivate-user'
        name = 'Deactivate User'
        resources = ("app-user",)
        tags = ["user", "deactivation"]
        auth_required = True
        description = "Deactivate user account"

    class Data(DataModel):
        reason: Optional[str] = None

    async def _process(self, agg, stm, payload):
        result = await agg.deactivate(self.user_id)
        yield agg.create_response(serialize_mapping(result), _type="user-response")

    @property
    def user_id(self):
        return self.aggroot.identifier


class ReconcileUser(Command):
    """Reconcile user account state"""

    class Meta:
        key = 'reconcile-user'
        name = 'Reconcile User'
        resources = ("app-user",)
        tags = ["user", "reconciliation"]
        auth_required = True
        description = "Reconcile user account state and data"

    class Data(DataModel):
        """No additional data required for reconciliation"""
        pass

    async def _process(self, agg, stm, payload):
        result = await agg.reconcile(self.user_id)
        yield agg.create_response(serialize_mapping(result), _type="user-response")

    @property
    def user_id(self):
        return self.aggroot.identifier
