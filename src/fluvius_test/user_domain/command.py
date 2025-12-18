from fluvius.data import serialize_mapping, DataModel
from .domain import UserDomain

processor = UserDomain.command_processor
Command = UserDomain.Command


class CreateUserCmd(Command):
	""" Create a new user account """

	class Meta:
		key = 'create-user'
		name = 'Create User'
		resource_init = True
		resource_docs = 'Resource key. e.g. `user`'

	class Data(DataModel):
		name: str

	async def _process(self, aggregate, statemgr, payload):
		user = await aggregate.create_user(payload)
		yield aggregate.create_message('user-message', test_message='sample-message-value')
		yield aggregate.create_response(serialize_mapping(user), _type="user-response")


class UpdateUserCmd(Command):
	""" Update a user account """
	class Meta:
		key = 'update-user'
		name = 'Update User'
		resources = ('user', )
		resource_docs = 'Resource key. e.g. `user`'

	class Data(DataModel):
		name: str

	async def _process(self, aggregate, statemgr, payload):
		await aggregate.update_user(payload)
		yield aggregate.create_response({"status": "success"}, _type="user-response")


class InvalidateUserCmd(Command):
	""" Invalidate a user account """

	class Meta:
		key = "invalidate-user"
		name = "Invalidate User"
		resources = ('user', )
		resource_docs = 'Resource key. e.g. `user`'

	async def _process(self, aggregate, statemgr, payload):
		await aggregate.invalidate_user()
