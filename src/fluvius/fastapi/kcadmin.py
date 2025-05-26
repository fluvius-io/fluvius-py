import os
import re
from aiohttp import BasicAuth, ClientSession
from fluvius.data import nullable, PClass, field
from fluvius.error import BadRequestError, ForbiddenError
from fluvius.fastapi import config, logger
from .restriction import RESTRICTION

SUCCESS_CODES = [200, 201, 202, 203, 204, 205, 206, 207, 208, 226]

URL_ADMIN_EVENT               = "admin/realms/{realm_name}/admin-events"
URL_ADMIN_GET_SESSIONS        = "admin/realms/{realm_name}/users/{id}/sessions"
URL_ADMIN_REALMS              = "admin/realms"
URL_ADMIN_RESET_PASSWORD      = "admin/realms/{realm_name}/users/{id}/reset-password"
URL_ADMIN_ROLE                = "admin/realms/{realm_name}/roles/{role_name}"
URL_ADMIN_SEND_UPDATE_ACCOUNT = "admin/realms/{realm_name}/users/{id}/execute-actions-email"
URL_ADMIN_SERVER_INFO         = "admin/serverinfo"
URL_ADMIN_USER                = "admin/realms/{realm_name}/users/{id}"
URL_ADMIN_USERS               = "admin/realms/{realm_name}/users"
URL_ADMIN_USERS_COUNT         = "admin/realms/{realm_name}/users/count"
URL_ADMIN_USER_ROLES          = "admin/realms/{realm_name}/users/{id}/role-mappings/realm"
URL_LOGIN_EVENT               = "admin/realms/{realm_name}/events"
URL_SEND_VERIFY_EMAIL         = "admin/realms/{realm_name}/users/{id}/send-verify-email"
URL_TOKEN                     = "realms/{realm_name}/protocol/openid-connect/token"


class KCUser(PClass):
    id                         = field(type=str)
    username                   = field(type=nullable(str))
    enabled                    = field(type=nullable(bool))
    totp                       = field(type=nullable(bool))
    emailVerified              = field(type=nullable(bool))
    firstName                  = field(type=nullable(str))
    lastName                   = field(type=nullable(str))
    email                      = field(type=nullable(str))
    createdTimestamp           = field(type=nullable(int))
    disableableCredentialTypes = field(type=nullable(list))
    requiredActions            = field(type=nullable(list))
    notBefore                  = field(type=nullable(int))
    access                     = field(type=nullable(dict))
    attributes                 = field(type=nullable(dict))


class KCRole(PClass):
    id          = field(type=str)
    name        = field(type=str)
    attributes  = field(type=nullable(dict))
    clientRole  = field(type=nullable(bool))
    composite   = field(type=nullable(bool))
    containerId = field(type=nullable(str))
    description = field(type=nullable(str))


class KCAdmin(object):
    def __init__(
        self,
        app,
        server_url,
        client_id,
        client_secret,
        realm_name,
        ssl_verify=True,
    ):
        self.server_url    = server_url
        self.realm_name    = realm_name
        self.client_id     = client_id
        self.client_secret = client_secret
        self.timeout       = 60
        self.ssl_verify    = ssl_verify
        
        if app:
            self.init_app(app)

    @property
    def session(self):
        if not hasattr(self, "_session"):
            self._session = ClientSession()
            self._session._request_class.ssl = self.ssl_verify
        return self._session

    async def get_token(self):
        session = self.session
        params_path = {"realm_name": self.realm_name}
        url = os.path.join(self.server_url, URL_TOKEN.format(**params_path))

        payload = {"grant_type": "client_credentials"}
        if self.client_secret:
            payload["client_secret_key"] = self.client_secret

        resp = await session.post(
            url=url,
            auth=BasicAuth(self.client_id, self.client_secret),
            data=payload,
            timeout=self.timeout,
        )
        token_resp = await resp.json()
        if token_resp.get("error_description"):
            raise ValueError(token_resp.get("error_description"))
        return token_resp["access_token"]

    async def auth_header(self):
        return {"Authorization": f"Bearer {await self.get_token()}"}

    def construct_url(self, *args):
        return os.path.join(*args)

    async def _request(self, method, endpoint, data=None, error_message=None, **kwargs):
        headers = await self.auth_header()
        url = self.construct_url(self.server_url, endpoint)
        func = self.session.request
        resp = await func(method=method, url=url, json=data, params=kwargs, timeout=self.timeout, headers=headers)
        if resp.status in SUCCESS_CODES:
            return resp

        try:
            data = await resp.json()
            resp_message = data["errorMessage"]
        except KeyError:
            resp_message = await resp.text()

        message = error_message if error_message else "Error request to keycloak"
        logger.info("/kcadmin/ %s: [%s] -> %s", message, resp.status, resp_message)
        raise ValueError(f"{message}: {resp_message}")


    async def _get(self, endpoint, **kwargs):
        return await self._request("GET", endpoint, **kwargs)

    async def _post(self, endpoint, data, **kwargs):
        return await self._request("POST", endpoint, data, **kwargs)

    async def _put(self, endpoint, data, **kwargs):
        return await self._request("PUT", endpoint, data, **kwargs)

    async def _delete(self, endpoint, data={}, **kwargs):
        return await self._request("DELETE", endpoint, data, **kwargs)

    async def get_user(self, user_id):
        endpoint = URL_ADMIN_USER.format(id=user_id, realm_name=self.realm_name)
        resp = await self._get(endpoint, error_message="Get user failed")
        data = await resp.json()
        return KCUser.create(data)

    async def get_role(self, role_name):
        endpoint = URL_ADMIN_ROLE.format(realm_name=self.realm_name, role_name=role_name)
        resp = await self._get(endpoint, error_message="Get role failed")
        return await resp.json()

    async def create_user(self, user_data):
        """
        user_data = {
            "email": "",
            "username": "",
            "firstName": "",
            "lastName": "",
            "enabled": "true",
            "requiredActions": ["VERIFY_EMAIL", "UPDATE_PASSWORD"],
            "credentials": [
                {
                    "value": "fiisoft.net",
                    "temporary": "false",
                    "type": "password",
                }
            ]
        }
        """
        self.email_restriction(user_data)
        endpoint = URL_ADMIN_USERS.format(realm_name=self.realm_name)
        resp = await self._post(endpoint, data=user_data, error_message="Create user failed")
        data = resp.headers.get("Location")
        return KCUser(id=data[-36:])

    async def execute_actions(self, user_id, actions, redirect_uri=None):
        # redirect_uri need to be set in keycloak be valid
        # "http://localhost:8080/"

        params_query = {"client_id": self.client_id}
        if redirect_uri:
            params_query["redirect_uri"] = redirect_uri

        endpoint = URL_ADMIN_SEND_UPDATE_ACCOUNT.format(realm_name=self.realm_name, id=user_id)
        resp = await self._put(endpoint, data=actions, error_message="Execute_actions failed", **params_query)
        return resp

    async def send_verify_email(self, user_id, redirect_uri=None):
        params_query = {}
        if redirect_uri:
            params_query["redirect_uri"] = redirect_uri

        endpoint = URL_SEND_VERIFY_EMAIL.format(realm_name=self.realm_name, id=user_id)
        resp = await self._put(endpoint, data={}, error_message="Send verify email failed", **params_query)
        return resp

    async def update_user(self, user_id, payload):
        endpoint = URL_ADMIN_USER.format(realm_name=self.realm_name, id=user_id)
        resp = await self._put(endpoint, data=payload, error_message="Update user failed")
        return resp

    async def delete_user(self, user_id):
        endpoint = URL_ADMIN_USER.format(realm_name=self.realm_name, id=user_id)
        resp = await self._delete(endpoint)
        return resp

    async def get_realms(self):
        return self.realm_name

    async def users_count(self, params_str=None):
        endpoint = f"{URL_ADMIN_USERS_COUNT.format(realm_name=self.realm_name)}?{params_str}"
        resp = await self._get(endpoint, error_message="Count user failed")
        return await resp.json()

    async def set_user_password(self, user_id, password, temporary=False):
        endpoint = URL_ADMIN_RESET_PASSWORD.format(realm_name=self.realm_name, id=user_id)
        payload = {"type": "password", "temporary": temporary, "value": password}
        resp = await self._put(endpoint, data=payload)
        return resp

    async def get_server_info(self):
        resp = await self._get(URL_ADMIN_SERVER_INFO)
        return resp

    async def get_users(self):
        # need to refactor
        endpoint = f"{URL_ADMIN_USERS.format(realm_name=self.realm_name)}?max=99999999"
        resp = await self._get(endpoint, error_message="Get users failed")
        return [KCUser.create(user) for user in await resp.json()]

    async def find_user(self, username):
        endpoint = URL_ADMIN_USERS.format(realm_name=self.realm_name)
        resp = await self._get(endpoint, error_message="Find users failed", search=username)
        return [KCUser.create(user) for user in await resp.json()]

    async def get_user_roles(self, user_id):
        endpoint = URL_ADMIN_USER_ROLES.format(realm_name=self.realm_name, id=user_id)
        resp = await self._get(endpoint, error_message="Get user roles failed")
        return [KCRole.create(role) for role in await resp.json()]

    async def add_user_roles(self, user_id, role_data):
        """
            role_data = [<role-name>]
            role_data = [
                "system-contract-manager",
                "system-credentialing-manager"
            ]
        """
        roles_data = [await self.get_role(role_name) for role_name in role_data]
        endpoint = URL_ADMIN_USER_ROLES.format(realm_name=self.realm_name, id=user_id)
        resp = await self._post(endpoint, data=roles_data, error_message="Add user roles failed")
        return resp

        await self._raise_error_message(resp, message="Add user roles failed")

    async def delete_user_roles(self, user_id, role_data):
        roles_data = [await self.get_role(role_name) for role_name in role_data]
        endpoint = URL_ADMIN_USER_ROLES.format(realm_name=self.realm_name, id=user_id)
        resp = await self._delete(endpoint, data=roles_data, error_message="Delete user roles failed")
        return resp

    async def get_login_events(self, date_from):
        endpoint = URL_LOGIN_EVENT.format(realm_name=self.realm_name, date_from=date_from.isoformat())
        resp = await self._get(endpoint, error_message="Get login events failed")
        return await resp.json()

    async def get_admin_events(self, date_from):
        endpoint = URL_ADMIN_EVENT.format(realm_name=self.realm_name, date_from=date_from.isoformat())
        resp = self._get(endpoint, error_message="Get admin events failed")
        return await resp.json()

    def check_whitelist_email(self, domain):
        if domain not in config.WHITELIST_DOMAIN:
            raise ForbiddenError(
                "F102-403",
                "To prevent member data exposure, this email address is not allowed to log in to the system."  # noqa: E501
            )

    def check_blacklist_email(self, domain):
        if domain in RESTRICTION:
            raise ForbiddenError(
                "F103-403",
                "To prevent member data exposure, this email address is not allowed to log in to the system."  # noqa: E501
            )

    def email_restriction(self, user_data):
        try:
            domain = re.search(
                r"(?<=@)(\S+$)", user_data.get("email")).group(0)
            if config.WHITELIST_DOMAIN:
                self.check_whitelist_email(domain)
            if config.BLACKLIST_DOMAIN:
                self.check_blacklist_email(domain)
        except AttributeError:
            raise BadRequestError(
                "F100-400",
                "Please input a valid email"
            )

    def init_app(self, app):
        self._app = app
        app.state.keycloak_admin = self
