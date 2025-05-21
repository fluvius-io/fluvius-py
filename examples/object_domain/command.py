from pydantic import BaseModel, ValidationError, Extra
from typing import Optional
from types import SimpleNamespace
from fluvius.data import BlankModel, DataModel, serialize_mapping, UUID_TYPE
from datetime import datetime

from .domain import _command, _processor, ObjectDomain
from . import logger

Command = ObjectDomain.Command

class PersonName(DataModel):
    family: str
    given: str
    middle: str
    title: Optional[str] = None

class UpdateObjectCmd(Command):
    ''' UpdateObject Command ...'''

    class Meta:
        key = 'update-object'
        tags = ("transaction",)
        resources = ("people-economist", )
        description = "Withdraw money"
        scope_required = {'domain_sid': UUID_TYPE}

    async def _process(self, aggregate, statemgr, payload):
        data = serialize_mapping(payload)

        ''' Demonstrate inline handler definition,
            NOTE: this should be a pure function - no reference to `self` or `cls` '''
        await aggregate.update(content=data)


class PersonModel(DataModel):
    name: PersonName
    birthdate: datetime
    job: str


class CreateObjectCmd(Command):
    ''' CreateObject Command ...'''
    class Meta:
        key = 'create-object'
        name = 'Create Generic Object'
        new_resource = True
        api_docs = 'Resource key. E.g. `people-economist`'

    Data = PersonModel

    def command_method_echo(self, *args):
        return args

    @_processor
    async def _process(self, aggregate, statemgr, payload):
        data = serialize_mapping(payload)
        aggroot = aggregate.get_aggroot()
        economist = statemgr.create('people-economist', data, _id=aggroot.identifier)
        logger.info('/3rd/ Non-annotated processor (default) called: %s', aggroot)
        yield aggregate.create_response(serialize_mapping(economist), _type="object-response")

    @_processor(priority=10)
    def _testing_high_priority(self, agg, stm, dat):
        logger.info('/1st/ HIGH PRIORITY [priority: 10] PROCESSOR CALLED. Kwargs: %s', self)

    @_processor
    async def testing_normal(self, agg, stm, dat):
        logger.info('/2nd/ SECOND PROCESSOR [priority: 0] CALLED: %s', dat)
        r = await stm.custom_query_echo(result='TEST VALUE')
        assert r['result'] == 'TEST VALUE'
        assert self.command_method_echo(1, 2, 3) == (1, 2, 3)


class RemoveObjectCmd(Command):
    class Meta:
        key = 'remove-object'
        scope_optional = {'domain_sid': UUID_TYPE}


@_processor(RemoveObjectCmd)
async def handle__remove_object(cmd, agg, sta, pay):
    await agg.remove()


# @_processor(
#     RemoveObjectCmd, UpdateObjectCmd, CreateObjectCmd
# )
# async def handle__logging(agg, sta, cmd, root):
#     ''' Demonstrate external handler definition, for handling multiple commands '''
#     await agg.log(cmd=cmd)
