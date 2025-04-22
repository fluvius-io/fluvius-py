from types import SimpleNamespace
from fluvius.domain import Command
from fluvius.data import BlankModel, DataModel
from .domain import _command, _processor
from . import logger


# class UpdateObjectBaseCmd(CommandDefinition):
#     def __invariant__(self):
#         content = self.payload

#         return (
#             (bool(content), "Pay load must not be empty. [%s]" % content),
#             (
#                 not content.get("_etag"),
#                 "Payload must not contain readonly fields.",
#             ),
#         )

#     payload = field(type=dict, mandatory=True)


@_command("update-object")
class UpdateObjectCmd(Command):
    class Meta:
        tags = ("transaction",)
        resources = ("people-economist", )
        description = "Withdraw money"
        endpoints = None

    class Payload(BlankModel):
        pass

    async def _process(self, aggregate, statemgr, payload, rootobj):
        data = serialize_model(payload)

        ''' Demonstrate inline handler definition,
            NOTE: this should be a pure function - no reference to `self` or `cls` '''
        await aggregate.update(content=data)


def serialize_model(payload):
    if isinstance(payload, dict):
        return payload

    if isinstance(payload, BlankModel):
        return payload.__dict__

    if isinstance(payload, DataModel):
        return DataModel.dict(payload)

    raise ValueError('Unable to serialize model')

@_command("create-object")
class CreateObjectCmd(Command):

    def command_method_echo(self, *args):
        return args

    async def _process(self, aggregate, statemgr, payload, rootobj):
        data = serialize_model(payload)
        economist = statemgr.create('people-economist', data)
        logger.info('/3rd/ Non-annotated processor (default) called: %s', rootobj)

        # Use: create_typed_resp(cmd.payload, resp_type="object-response") if needed
        yield aggregate.create_response(data)
        yield aggregate.create_typed_resp("object-response", data)

    @_processor(priority=10)
    def _testing_high_priority(self, agg, stm, dat, ref):
        logger.info('/1st/ HIGH PRIORITY [priority: 10] PROCESSOR CALLED. Kwargs: %s', self)

    @_processor
    async def testing_normal(self, agg, stm, dat, ref):
        logger.info('/2nd/ SECOND PROCESSOR [priority: 0] CALLED: %s', dat)
        r = await stm.custom_query_echo(result='TEST VALUE')
        assert r['result'] == 'TEST VALUE'
        assert self.command_method_echo(1, 2, 3) == (1, 2, 3)


@_command("remove-object")
class RemoveObjectCmd(Command):
    pass


@_processor(RemoveObjectCmd)
async def handle__remove_object(cmd, agg, sta, pay, root):
    await agg.remove()


# @_processor(
#     RemoveObjectCmd, UpdateObjectCmd, CreateObjectCmd
# )
# async def handle__logging(agg, sta, cmd, root):
#     ''' Demonstrate external handler definition, for handling multiple commands '''
#     await agg.log(cmd=cmd)
