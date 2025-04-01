import pytest

from fluvius.domain import context, identifier, Event
from object_example.domain import ObjectDomain
from object_example.storage import PeopleEconomistResource, populate_fixture_data


FIXTURE_ID = identifier.UUID_GENF("100")


@pytest.fixture
async def ctx():
    return context.DomainContext(
        domain='test',
        user_id=FIXTURE_ID,
        revision=0,
        headers={
            "if-match": "RNDFIX:QVWxxb9UuRr3vvYEZF3wZGFdBWc"
        },
        transport=context.DomainTransport.SANIC,
    )


def clean_state(state):
    NON_PURE_FIELDS = ('_etag', '_updated', '_created', '_updater', '_creator')

    def _filter():
        for k, v in state.items():
            if k in NON_PURE_FIELDS:
                continue

            if isinstance(v, dict):
                yield k, clean_state(v)
            else:
                yield k, v

    return dict(_filter())


@pytest.mark.asyncio
async def test_object_domain(ctx):
    await populate_fixture_data()
    domain = ObjectDomain()
    # aggroot = domain.create_aggroot('people-economist', FIXTURE_ID)

    id1 = identifier.UUID_GENF("ABC123")
    create_payload = {
        '_id': id1,  # Pin down the ID for easier testing,
        'job': 'physicist',
        'name': {'family': 'Keynes', 'given': 'John', 'middle': 'Maynard'}
    }

    update_command = domain.create_command('update-object', 'people-economist', FIXTURE_ID, {'job': 'economist'})
    create_command = domain.create_command('create-object', 'people-economist', FIXTURE_ID, create_payload)
    remove_command = domain.create_command('remove-object', 'people-economist', FIXTURE_ID, None)

    resps = await domain.handle_request(ctx, update_command, create_command, remove_command)
    # state = domain.statemgr

    # assert all(isinstance(evt, Event) for evt in evts) and len(evts) == 6
    # assert state.item_modified('people-economist', FIXTURE_ID)
    # await state.persist()
    # assert not state.item_modified('people-economist', FIXTURE_ID)
