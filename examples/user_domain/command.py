from fluvius.data import serialize_mapping, DataModel
from .domain import IDMDomain

processor = IDMDomain.command_processor


class CreateUserCmd(IDMDomain.Command):
	""" Create a new user account """

	class Meta:
		key = 'create-user'
		name = 'Create User'
		new_resource = True
		resource_docs = 'Resource key. e.g. `user`'

	class Data(DataModel):
		name: str

	@processor
	async def process(self, aggregate, statemgr, payload):
		data = serialize_mapping(payload)
		user = yield aggregate.create_user(data)
		yield aggregate.create_response(serialize_mapping(user), _type="user-response")
