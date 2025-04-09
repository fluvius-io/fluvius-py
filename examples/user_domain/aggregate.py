from object_domain.aggregate import ObjectAggregate
from . import logger


class UserAggregate(ObjectAggregate):
    @property
    def client(self):
        if not hasattr(self, '__oauth_client__'):
            request = self.context.request
            session = request['session']
            factory_args = {'access_token': session['access_token']}
            oauth_provider = session.get('oauth_provider')
            if oauth_provider:
                factory_args['provider'] = oauth_provider
            self.__oauth_client__ = self.context.app.oauth_factory(**factory_args)

        return self.__oauth_client__

    async def do__execute_actions(self, user_id, actions):
        return self.create_event('user-action-executed', data=dict(actions=actions))

    async def do__deactivate(self, user_id):
        return self.create_event('user-action-executed', data=dict(actions=['deactivate']))

    async def do__reconcile(self, user_id):
        return self.create_event('user-reconciled', data=dict(actions=['deactivate']))
