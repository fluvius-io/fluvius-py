import pytest
import asyncio
from fluvius.fastapi.kcadmin import KCAdmin, KCUser
from fluvius.fastapi import config, logger

@pytest.fixture(scope="session")
def event_loop():
    return asyncio.get_event_loop()

@pytest.fixture(scope="module")
def keycloak_admin():
    return KCAdmin(
        app=None,
        server_url=config.KEYCLOAK_BASE_URL,
        client_id=config.KEYCLOAK_CLIENT_ID,
        client_secret=config.KEYCLOAK_CLIENT_SECRET,
        realm_name=config.KEYCLOAK_REALM,
        ssl_verify=False,
    )

@pytest.mark.asyncio
async def test_create_and_get_user(keycloak_admin):
    email = "testuser@example.com"
    username = "testuser"
    user_data = {
        "email": email,
        "username": username,
        "firstName": "Test",
        "lastName": "User",
        "enabled": True,
        "credentials": [
            {
                "value": "test-password",
                "temporary": False,
                "type": "password",
            }
        ],
    }

   	# ======== Create user =========
    created_user = await keycloak_admin.create_user(user_data)
    assert isinstance(created_user, KCUser)
    assert created_user.id is not None

    # ======== Get user =========
    fetched_user = await keycloak_admin.get_user(created_user.id)
    assert fetched_user.username == username
    assert fetched_user.email == email

    # ======== Update user =========
    lastname = "User Updated"
    payload = {"lastName": lastname}
    await keycloak_admin.update_user(created_user.id, payload)
    fetched_user = await keycloak_admin.get_user(created_user.id)
    assert fetched_user.lastName == lastname

   	# ======== Test user action ======
   	# ======== Test send verification ======

   	# ======== Test delete user ======
    await keycloak_admin.delete_user(created_user.id)

    await keycloak_admin.session.close()
