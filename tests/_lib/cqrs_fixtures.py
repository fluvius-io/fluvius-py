from pyrsistent import field
from fluvius.domain.datadef import DomainResource, UUID_GENF
from object_domain.storage import ObjectDAL

FIXTURE_ID = UUID_GENF("100")


@ObjectDAL.register('people-economist')
class PeopleEconomistResource(DomainResource):
    job = field()
    name = field(type=dict)

    @classmethod
    async def reset_fixture_data(cls):
        item = PeopleEconomistResource.create({
            '_id': FIXTURE_ID,
            'name': {
                'given': 'Adam',
                'family': 'Smith'
            },
            '_etag': 'RNDFIX:QVWxxb9UuRr3vvYEZF3wZGFdBWc'
        })

        await ObjectDAL.insert(PeopleEconomistResource, item)

