import base64
import httpx
import json

from authlib.integrations.starlette_client import OAuth
from authlib.jose import jwt, JsonWebKey
from authlib.jose.util import extract_header
from fastapi import Request, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse
from functools import wraps
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from types import SimpleNamespace


from fluvius.error import UnauthorizedError
from fluvius.data import DataModel
from fluvius.auth import AuthorizationContext, KeycloakTokenPayload, SessionProfile, SessionOrganization, event as auth_event
from fluvius.helper import when

from pydantic import AnyUrl, EmailStr
from uuid import UUID
from pipe import Pipe
from typing import Literal, Optional, Awaitable, Callable
from urllib.parse import urlparse

from .setup import on_startup
from .helper import uri, generate_client_token, generate_session_id

from . import config, logger

IDEMPOTENCY_KEY = config.RESP_HEADER_IDEMPOTENCY
DEVELOPER_MODE = config.DEVELOPER_MODE
SAFE_REDIRECT_DOMAINS = config.SAFE_REDIRECT_DOMAINS


def auth_required(inject_ctx=True, **kwargs):
    def decorator(endpoint):
        @wraps(endpoint)
        async def wrapper(request: Request, *args, **kwargs):
            if not getattr(request.state, 'auth_context', None):
                raise HTTPException(status_code=401, detail="Not authenticated.")

            return await endpoint(request, *args, **kwargs)

        return wrapper
    return decorator



def is_safe_redirect_url(url: str) -> bool:
    """
    Validates if a given URL is a safe redirect:
    - It's either relative (no scheme or netloc),
    - Or it's an absolute URL pointing to a whitelisted domain.

    Args:
        url (str): The URL to validate.
        whitelist_domains (list[str]): List of allowed domains (e.g. ["example.com"]).

    Returns:
        bool: True if safe, False otherwise.
    """
    try:
        if not url:
            return False

        parsed = urlparse(url)

        # Case 1: Relative URL (e.g., "/login")
        if not parsed.netloc and not parsed.scheme:
            return True

        # Case 2: Absolute URL with whitelisted domain
        domain = parsed.hostname

        if '*' in SAFE_REDIRECT_DOMAINS:
            return True

        if domain and domain.lower() in SAFE_REDIRECT_DOMAINS:
            return True

        return False

    except Exception:
        return False

def validate_direct_url(url: str, default: str) -> str:
    if is_safe_redirect_url(url):
        return url

    return default

class FluviusAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, auth_profile_provider):
        super().__init__(app)
        provider_cls = FluviusAuthProfileProvider.get(auth_profile_provider)
        self.get_auth_context = provider_cls(app).get_auth_context

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        try:
            auth_context = await self.get_auth_context(request)
            request.state.auth_context = auth_context
        except Exception as e:
            logger.exception(e)
            raise

        response = await call_next(request)

        if idem_key := request.headers.get(IDEMPOTENCY_KEY):
            response.headers[IDEMPOTENCY_KEY] = idem_key

        return response


class FluviusAuthProfileProvider(object):
    _REGISTRY = {}

    def __init_subclass__(cls):
        super().__init_subclass__()

        key = cls.__name__
        if key in FluviusAuthProfileProvider._REGISTRY:
            raise ValueError(f'Auth Profile Provider is already registered: {key} => {FluviusAuthProfileProvider._REGISTRY[key]}')

        FluviusAuthProfileProvider._REGISTRY[key] = cls
        DEVELOPER_MODE and logger.info('Registered Auth Profile Provider: %s', cls.__name__)

    @classmethod
    def get(cls, key):
        if key is None:
            return FluviusAuthProfileProvider

        try:
            return FluviusAuthProfileProvider._REGISTRY[key]
        except KeyError:
            raise ValueError(f'Auth Profile Provider is not valid: {key}. Available: {list(FluviusAuthProfileProvider._REGISTRY.keys())}')

    """ Lookup services for user related info """
    def __init__(self, app):
        self._app = app

    def authorize_claims(self, claims_token: dict) -> KeycloakTokenPayload:
        return KeycloakTokenPayload(**claims_token)

    def get_auth_token(self, request: Request) -> Optional[str]:
        # You can optionally decode and validate the token here
        if not (id_token := request.cookies.get("id_token")):
            return None

        return request.session.get("user")

    async def get_auth_context(self, request: Request) -> Optional[AuthorizationContext]:
        try:
            auth_token = self.get_auth_token(request)
            if not auth_token:
                return None
            auth_user = self.authorize_claims(auth_token)
        except (KeyError, ValueError):
            raise UnauthorizedError("Q4031216", "Authorization Failed: Missing or invalid  claims token")

        auth_context = await self.setup_context(auth_user)
        auth_context.session_id = auth_token.get('session_id')
        auth_context.client_token = auth_token.get('client_token')
        return auth_context


    async def setup_context(self, auth_user: KeycloakTokenPayload) -> AuthorizationContext:
        profile = SessionProfile(
            id=auth_user.jti,
            name=auth_user.name,
            family_name=auth_user.family_name,
            given_name=auth_user.given_name,
            email=auth_user.email,
            username=auth_user.preferred_username,
            roles=('user', 'staff', 'provider'),
            org_id=auth_user.sub,
            usr_id=auth_user.sid
        )

        organization = SessionOrganization(
            id=auth_user.sub,
            name=auth_user.family_name
        )
        iamroles = ('sysadmin', 'operator')
        realm = 'default'

        return AuthorizationContext(
            realm = realm,
            user = auth_user,
            profile = profile,
            organization = organization,
            iamroles = iamroles
        )


@Pipe
def configure_authentication(app, config=config, base_path="/auth", auth_profile_provider=None):
    auth_profile_provider = auth_profile_provider or config.AUTH_PROFILE_PROVIDER

    def api(*paths, method=app.get):
        return method(uri(base_path, *paths), tags=["Authentication"])

    def _setup_oauth():
        app.openapi_tags = app.openapi_tags or []
        app.openapi_tags.append({
            "name": "Authentication",
            "description": "OAuth/JWT authentication endpoints"
        })

        # === OAuth Setup ===
        oauth = OAuth()
        oauth.register(
            name='keycloak',
            server_metadata_url=KEYCLOAK_METADATA_URI,
            client_id=config.KEYCLOAK_CLIENT_ID,
            client_secret=config.KEYCLOAK_CLIENT_SECRET,
            client_kwargs={"scope": "openid profile email"},
            redirect_uri=config.DEFAULT_CALLBACK_URI,
        )

        app.add_middleware(FluviusAuthMiddleware, auth_profile_provider=auth_profile_provider)
        app.add_middleware(
            SessionMiddleware,
            secret_key=config.APPLICATION_SECRET_KEY,
            session_cookie=config.SESSION_COOKIE,
            https_only=config.COOKIE_HTTPS_ONLY,
            same_site=config.COOKIE_SAME_SITE_POLICY
        )

        return oauth

    def extract_jwt_kid(token: str) -> dict:
        header_segment = token.split('.')[0]
        padded = header_segment + '=' * (-len(header_segment) % 4)
        decoded = base64.urlsafe_b64decode(padded)
        return json.loads(decoded)['kid']

    def extract_jwt_key(jwks_keyset, token):
        # This will parse the JWT and extract both the header and payload
        kid = extract_jwt_kid(token)

        # 🔍 Find the correct key by kid
        try:
            return next(k for k in jwks_keyset.keys if k.kid == kid)
        except StopIteration:
            raise HTTPException(status_code=401, detail="Public key not found for kid")

    async def decode_ac_token(jwks_keyset, ac_token: str):
        # This will parse the JWT and extract both the header and payload
        key = extract_jwt_key(jwks_keyset, ac_token)
        return jwt.decode(ac_token, key)

    async def decode_id_token(jwks_keyset, id_token: str):
        key = extract_jwt_key(jwks_keyset, id_token)

        # Decode and validate
        claims = jwt.decode(
            id_token,
            key=key,
            claims_options={
                "iss": {"essential": True, "value": KEYCLOAK_ISSUER},
                "aud": {"essential": True, "value": config.KEYCLOAK_CLIENT_ID},
                "exp": {"essential": True},
            }
        )

        claims.validate()

        return claims

    # Async code at server startup
    @on_startup
    async def fetch_jwks_on_startup(app):
        async with httpx.AsyncClient() as client:
            response = await client.get(KEYCLOAK_JWKS_URI)
            data = response.json()

        app.state.jwks_keyset = JsonWebKey.import_key_set(data)  # Store JWKS in app state

    # === Routes ===
    @api()
    async def home():
        return {"message": "Go to /login to start OAuth2 login with Keycloak"}

    @api("login")
    async def login(request: Request):
        request.session["next"] = request.query_params.get('next')
        callback_uri = validate_direct_url(request.query_params.get('callback'), config.DEFAULT_CALLBACK_URI)
        return await oauth.keycloak.authorize_redirect(request, callback_uri)

    @api("callback")
    async def oauth_callback(request: Request):
        token = await oauth.keycloak.authorize_access_token(request)
        id_token = token.get(config.SES_ID_TOKEN_FIELD)
        ac_token = token.get(config.SES_AC_TOKEN_FIELD)

        if not id_token:
            raise HTTPException(status_code=400, detail="Missing ID token")

        id_data = await decode_id_token(request.app.state.jwks_keyset, id_token)
        ac_data = await decode_ac_token(request.app.state.jwks_keyset, ac_token)

        id_data.update(
            realm_access=ac_data.get("realm_access"),
            resource_access=ac_data.get("resource_access"),
            client_token=generate_client_token(request.session),
            session_id=generate_session_id(request.session)
        )

        request.session[config.SES_USER_FIELD] = id_data
        next_url = validate_direct_url(request.session["next"], config.DEFAULT_SIGNIN_REDIRECT_URI)
        response = RedirectResponse(url=next_url)
        response.set_cookie(config.SES_ID_TOKEN_FIELD, id_token)
        auth_event.authorization_success.send(request, user=id_data)

        return response

    @api("verify")
    @auth_required()
    async def verify_auth(request: Request):
        if not (user := request.state.auth_context.user):
            raise HTTPException(status_code=401, detail=f"Not logged in: {user}")

        return {
            "message": f"OK",
            "context": request.state.auth_context,
            "headers": dict(request.headers) | {"cookie": "<redacted>"}
        }

    @api("info")
    @auth_required()
    async def info(request: Request):
        return request.state.auth_context

    @api("logout")
    @auth_required()
    async def logout(request: Request):
        ''' Log out user locally (only for this API) '''
        user = request.session.get(config.SES_USER_FIELD)
        auth_event.user_logout.send(request, user=user)
        request.session.clear()
        redirect_uri = validate_direct_url(
            request.query_params.get('redirect'),
            config.DEFAULT_LOGOUT_REDIRECT_URI
        )
        return RedirectResponse(url=redirect_uri)  # Redirect after logout


    @api("signoff", method=app.post)
    async def sign_off(request: Request):
        ''' Log out user globally (including Keycloak) '''
        # 2. Logout from Keycloak using the logout endpoint
        access_token = request.cookies.get(config.SES_ID_TOKEN_FIELD)
        if not access_token:
            raise HTTPException(status_code=400, detail="No access token found")

        async with httpx.AsyncClient() as client:
            # Make the request to Keycloak's logout endpoint
            logout_response = await client.get(
                KEYCLOAK_LOGOUT_URI,
                params={"id_token": access_token},
            )

            if logout_response.status_code != 200:
                raise HTTPException(status_code=logout_response.status_code, detail=f"Keycloak logout failed {logout_response}: {access_token}")

        # 1. Clear FastAPI session/cookie
        # Assuming you're storing the JWT token in a secure cookie

        redirect_uri = validate_direct_url(request.query_params.get('redirect'), config.DEFAULT_LOGOUT_REDIRECT_URI)
        response = RedirectResponse(url=redirect_uri)  # Redirect after logout
        response.delete_cookie(config.SES_ID_TOKEN_FIELD)  # Clear the access_token cookie
        request.session.clear()

        return response

    # === Keycloak Configuration ===

    KEYCLOAK_ISSUER = uri(config.KEYCLOAK_BASE_URL, "realms", config.KEYCLOAK_REALM)
    KEYCLOAK_JWKS_URI = uri(KEYCLOAK_ISSUER, "protocol/openid-connect/certs")
    KEYCLOAK_LOGOUT_URI = uri(KEYCLOAK_ISSUER, "protocol/openid-connect/logout")
    KEYCLOAK_METADATA_URI = uri(KEYCLOAK_ISSUER, ".well-known/openid-configuration")

    oauth = _setup_oauth()
    return app
