from copy import deepcopy
from fluvius.domain.event_store import InMemoryEventStore
from fluvius.domain.command_store import InMemoryCommandStore
from fluvius.domain import state, identifier, context

FIXTURE_ID = identifier.UUID_GENF(100)
BASE_STATE = {
    ('app-user', FIXTURE_ID): {
        '_id': FIXTURE_ID,
        'name': {
            'given': 'Adam',
            'family': 'Smith'
        },
        '_etag': 'RNDFIX:jtVIbhVOV6hKGfpxQIFFUbjVY8I'
    }
}


class DummyDataFeed(object):
    def __init__(self, ctx: context.Context):
        self.__context__ = ctx
        self.__storage__ = deepcopy(BASE_STATE)
        self.history = []
        self.id_seed = 100

    def next_id(self, resource):
        ''' Deterministic ID generation '''

        self.id_seed += 1
        return identifier.UUID_GENF(self.id_seed)

    def find_one(self, resource, _id):
        return self.storage[resource, _id]

    def save(self, resource, _id, item, _etag=None):
        self.storage[resource, _id] = item
        return item

    def remove(self, resource, _id, _etag=None):
        return self.storage.pop((resource, _id), None)

    @property
    def storage(self):
        return self.__storage__


class DummyStateManager(state.StateManager):
    DataStorageClass = DummyDataFeed
    EventStorageClass = InMemoryEventStore
    CommandStorageClass = InMemoryCommandStore
