from fluvius.domain.event_store import EventStore
from fluvius.domain.command_store import CommandStore
from fluvius.domain.state import StateManager

from sanic_motor import BaseModel


class EventModel(BaseModel):
    __coll__ = "cqrs.event-store"


class CommandModel(BaseModel):
    __coll__ = "cqrs.command-store"


class MongoEventStore(EventStore):
    async def add_event(self, event):
        return await EventModel.insert_one(event.to_python())

    async def get_event(self, evt_id):
        return await EventModel.find_one({"_id": evt_id})


class MongoCommandStore(CommandStore):
    async def add_command(self, command):
        return await CommandModel.insert_one(command.to_python())

    async def get_command(self, cmd_id):
        return await CommandModel.find_one({"_id": cmd_id})


class MongoStateManager(StateManager):
    EventStorageClass = MongoEventStore
    CommandStorageClass = MongoCommandStore
