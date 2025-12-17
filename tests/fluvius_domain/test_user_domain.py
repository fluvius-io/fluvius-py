import pytest
from pytest import mark
from sqlalchemy import text
from fluvius_test.user_domain.domain import UserDomain
from fluvius_test.user_domain.model import UserConnector
from fluvius.data import UUID_GENR
from fluvius.domain.context import DomainTransport
from fluvius.data import UUID_GENR


FIXTURE_REALM = "signalflows-engine-testing"
FIXTURE_USER_ID = "88212396-02c5-46ae-a2ad-f3b7eb7579c0"
FIXTURE_ORGANIZATION_ID = "05e8bb7e-43e6-4766-98d9-8f8c779dbe45"
FIXTURE_PROFILE_ID = "f3f3bcc3-7f35-4d3a-aade-a6ec187e8b4f"

async def command_handler(domain, cmd_key, payload, resource, identifier, scope={}, context={}):
    _context = dict(
        headers=dict(),
        transport=DomainTransport.FASTAPI,
        source="signalflows-engine",
        realm=FIXTURE_REALM,
        user_id=FIXTURE_USER_ID,
        organization_id=FIXTURE_ORGANIZATION_ID,
        profile_id=FIXTURE_PROFILE_ID
    )
    if context:
        _context.update(**context)

    with domain.session(None, **_context):
        command = domain.create_command(
            cmd_key,
            payload,
            aggroot=(
                resource,
                identifier,
                scope.get('domain_sid'),
                scope.get('domain_iid'),
            )
        )

        return await domain.process_command(command)


@pytest.fixture
def domain():
    return UserDomain(None)


@mark.asyncio
async def test_create_user(domain):
    db = domain.statemgr.connector.engine
    async with db.begin() as conn:
        await conn.run_sync(UserConnector.__data_schema_base__.metadata.drop_all)
        await conn.run_sync(UserConnector.__data_schema_base__.metadata.create_all)

    user_id = UUID_GENR()
    payload = {
        "name": "John Doe"
    }
    result = await command_handler(domain, "create-user", payload, "user", user_id, context={"user_id": user_id})
    async with domain.statemgr.transaction():
        user = await domain.statemgr.fetch('user',user_id)
        assert user.name == "John Doe"

    update_payload = {"name": "Jane Doe Updated"}
    result = await command_handler(domain, "update-user", update_payload, "user", user_id, context={"user_id": user_id})
    async with domain.statemgr.transaction():
        user = await domain.statemgr.fetch('user',user_id)
        assert user.name == "Jane Doe Updated"

    result = await command_handler(domain, "invalidate-user", None, "user", user_id, context={"user_id": user_id})
    async with domain.statemgr.transaction():
        user = await domain.statemgr.find_one('user', identifier=user_id)
        assert user is None
