import inspect
import os

from fluvius.data.data_driver import InMemoryDriver
from fluvius.data import UUID_GENF, field, DataModel
from fluvius.domain import logger, ImmutableDomainResource


class ObjectExampleConnector(InMemoryDriver):
    pass


@ObjectExampleConnector.register_schema('people-economist')
class PeopleEconomistResource(ImmutableDomainResource):
    job = field()
    name = field(type=dict)


async def populate_fixture_data():
    connector = ObjectExampleConnector()
    connector.connect()
    async with connector.transaction():
        economist = PeopleEconomistResource.create({
            '_id': UUID_GENF("100"),
            'name': {
                'given': 'Adam',
                'family': 'Smith'
            },
            '_etag': 'RNDFIX:QVWxxb9UuRr3vvYEZF3wZGFdBWc'
        })

        item = await connector.insert('people-economist', economist)
