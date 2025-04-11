from fluvius.domain import CommandEnvelop
from fluvius.domain.datadef import field
from .domain import _command, _processor
from . import logger


class UpdateObjectBaseCmd(CommandEnvelop):
    def __invariant__(self):
        content = self.payload

        return (
            (bool(content), "Pay load must not be empty. [%s]" % content),
            (
                not content.get("_etag"),
                "Payload must not contain readonly fields.",
            ),
        )

    payload = field(type=dict, mandatory=True)


@_command("update-object")
class UpdateObjectCmd(UpdateObjectBaseCmd):
    class Meta:
        tags = ["transaction"]
        resource = "bank-account"
        description = "Withdraw money"

    async def _process(agg, sta, cmd, root):
        ''' Demonstrate inline handler definition,
            NOTE: this should be a pure function - no reference to `self` or `cls` '''
        await agg.update(content=cmd.payload)


@_command("create-object", fetch=False)
class CreateObjectCmd(UpdateObjectBaseCmd):
    def command_method_echo(self, *args):
        return args

    async def _process(agg, sta, cmd, ref):
        economist = sta.create('people-economist', **cmd.payload)
        logger.info('/3rd/ Non-annotated processor (default) called: %s', ref)

        # Use: create_typed_resp(cmd.payload, resp_type="object-response") if needed
        yield agg.create_response(cmd.payload)
        yield agg.create_typed_resp("object-response", cmd.payload)

    @_processor(priority=10)
    def testing_high_priority(agg, sta, cmd, ref):
        logger.info('/1st/ HIGH PRIORITY [priority: 10] PROCESSOR CALLED. Kwargs: %s', cmd)

    @_processor
    async def testing_normal(agg, sta, cmd, ref):
        logger.info('/2nd/ SECOND PROCESSOR [priority: 0] CALLED: %s', cmd)
        r = await sta.custom_query_echo(result='TEST VALUE')
        assert r['result'] == 'TEST VALUE'
        assert cmd.command_method_echo(1, 2, 3) == (1, 2, 3)


@_command("remove-object")
class RemoveObjectCmd(CommandEnvelop):
    pass


@_processor(RemoveObjectCmd)
async def handle__remove_object(agg, sta, cmd, root):
    await agg.remove()


@_processor(
    RemoveObjectCmd, UpdateObjectCmd, CreateObjectCmd
)
async def handle__logging(agg, sta, cmd, root):
    ''' Demonstrate external handler definition, for handling multiple commands '''
    await agg.log(cmd=cmd)
