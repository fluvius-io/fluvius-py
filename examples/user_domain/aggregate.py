from fluvius.domain.aggregate import Aggregate, action
from fluvius.data import timestamp
from . import logger


class UserAggregate(Aggregate):
    """Aggregate for handling user domain operations"""

    @property
    def client(self):
        """OAuth client for external integrations"""
        if not hasattr(self, '__oauth_client__'):
            request = self.context.request
            session = request['session']
            factory_args = {'access_token': session['access_token']}
            oauth_provider = session.get('oauth_provider')
            if oauth_provider:
                factory_args['provider'] = oauth_provider
            self.__oauth_client__ = self.context.app.oauth_factory(**factory_args)

        return self.__oauth_client__

    @action("user-action-executed", resources="user")
    async def execute_actions(self, user_id, actions):
        """Execute specified actions for a user"""
        user = await self.fetch_aggroot()
        
        # Update user with executed actions
        updated_user = await self.statemgr.update(
            user, 
            last_action_executed=timestamp(),
            executed_actions=actions
        )
        
        return self.create_event(
            'user-action-executed', 
            target=self.aggroot,
            data={'actions': actions, 'timestamp': timestamp()}
        )

    @action("user-deactivated", resources="user")
    async def deactivate(self, user_id):
        """Deactivate a user account"""
        user = await self.fetch_aggroot()
        
        # Update user status to deactivated
        updated_user = await self.statemgr.update(
            user,
            status='deactivated',
            deactivated_at=timestamp()
        )
        
        return self.create_event(
            'user-deactivated',
            target=self.aggroot,
            data={'deactivated_at': timestamp()}
        )

    @action("user-reconciled", resources="user")
    async def reconcile(self, user_id):
        """Reconcile user account data"""
        user = await self.fetch_aggroot()
        
        # Perform reconciliation logic
        updated_user = await self.statemgr.update(
            user,
            last_reconciled=timestamp()
        )
        
        return self.create_event(
            'user-reconciled',
            target=self.aggroot,
            data={'reconciled_at': timestamp()}
        )

    @action("user-totp-removed", resources="user")
    async def remove_totp(self, user_id):
        """Remove TOTP authentication from user"""
        user = await self.fetch_aggroot()
        
        # Remove TOTP settings
        updated_user = await self.statemgr.update(
            user,
            totp_enabled=False,
            totp_removed_at=timestamp()
        )
        
        return self.create_event(
            'user-totp-removed',
            target=self.aggroot,
            data={'removed_at': timestamp()}
        )
