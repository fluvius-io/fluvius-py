import base64
import httpx
import json
from urllib.parse import urlencode

from authlib.integrations.starlette_client import OAuth
from authlib.jose import jwt, JsonWebKey
from authlib.jose.util import extract_header
from fastapi import Request, Depends, HTTPException, Response
from fastapi.responses import RedirectResponse, JSONResponse
from functools import wraps
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from types import SimpleNamespace


<<<<<<< HEAD
from fluvius.error import UnauthorizedError, BadRequestError
=======
from fluvius.error import UnauthorizedError, FluviusException
>>>>>>> origin/main
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

        if isinstance(auth_profile_provider, str):
            provider_cls = FluviusAuthProfileProvider.get(auth_profile_provider)
        elif issubclass(auth_profile_provider, FluviusAuthProfileProvider):
            provider_cls = auth_profile_provider
        else:
            raise BadRequestError('S00.001', f'Invalid Auth Profile Provider: {auth_profile_provider}')

        self.get_auth_context = provider_cls(app).get_auth_context

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        try:
            auth_context = await self.get_auth_context(request)
            request.state.auth_context = auth_context
        except FluviusException as e:
            # Handle FluviusException directly in middleware to ensure proper status codes
            # Exceptions raised in middleware may not always be caught by FastAPI's exception handlers
            content = e.content
            if DEVELOPER_MODE:
                import traceback
                content = content or {}
                content['traceback'] = traceback.format_exc()
            return JSONResponse(
                status_code=e.status_code,
                content=content
            )
        except Exception as e:
            logger.exception(e)
            raise JSONResponse(
                status_code=500,
                content={"errcode": "A500000", "message": str(e)}
            )

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
            raise BadRequestError('S00.002', f'Auth Profile Provider is already registered: {key} => {FluviusAuthProfileProvider._REGISTRY[key]}')

        FluviusAuthProfileProvider._REGISTRY[key] = cls
        DEVELOPER_MODE and logger.info('Registered Auth Profile Provider: %s', cls.__name__)

    @classmethod
    def get(cls, key):
        if key is None:
            return FluviusAuthProfileProvider

        try:
            return FluviusAuthProfileProvider._REGISTRY[key]
        except KeyError:
            raise BadRequestError('S00.003', f'Auth Profile Provider is not valid: {key}. Available: {list(FluviusAuthProfileProvider._REGISTRY.keys())}')

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
            raise UnauthorizedError("S00.004", "Authorization Failed: Missing or invalid claims token")

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
def configure_authentication(app, config=config, base_path="/auth", auth_profile_provider=config.AUTH_PROFILE_PROVIDER):
    def api(*paths, method=app.get, **kwargs):
        return method(uri(base_path, *paths), tags=["Authentication"], **kwargs)

    def setup_oauth():
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
            "status": "OK",
            "message": f"User logged in.",
            "context": request.state.auth_context,
            "headers": dict(request.headers) | {"cookie": "<redacted>"}
        }

    @api("info")
    @auth_required()
    async def info(request: Request):
        return request.state.auth_context

    @api("sign-in")
    async def sign_in(request: Request):
        request.session["next"] = request.query_params.get('next')
        callback_uri = validate_direct_url(request.query_params.get('callback'), config.DEFAULT_CALLBACK_URI)
        return await oauth.keycloak.authorize_redirect(request, callback_uri)

    @api("sign-up")
    async def sign_up(request: Request):
        return RedirectResponse(url=KEYCLOAK_SIGNUP_URI)

    @api("sign-out")
    @auth_required()
    async def sign_out(request: Request):
        ''' Log out user globally (including Keycloak) '''

        redirect_uri = validate_direct_url(
            request.query_params.get('redirect_uri'),
            config.DEFAULT_LOGOUT_REDIRECT_URI
        )
        
        access_token = request.cookies.get(config.SES_ID_TOKEN_FIELD)
        if not access_token:
            raise HTTPException(status_code=400, detail="No access token found")

        keycloak_logout_url = f"{KEYCLOAK_LOGOUT_URI}?{urlencode({'id_token_hint': access_token, 'post_logout_redirect_uri': redirect_uri})}"
        request.session.clear()
        response = RedirectResponse(url=keycloak_logout_url)
        response.delete_cookie(config.SES_ID_TOKEN_FIELD)

        return response

    # === Keycloak Configuration ===

    KEYCLOAK_ISSUER = uri(config.KEYCLOAK_BASE_URL, "realms", config.KEYCLOAK_REALM)
    KEYCLOAK_JWKS_URI = uri(KEYCLOAK_ISSUER, "protocol/openid-connect/certs")
    KEYCLOAK_LOGOUT_URI = uri(KEYCLOAK_ISSUER, "protocol/openid-connect/logout")
    KEYCLOAK_SIGNUP_URI = uri(KEYCLOAK_ISSUER, "protocol/openid-connect/registrations")
    KEYCLOAK_METADATA_URI = uri(KEYCLOAK_ISSUER, ".well-known/openid-configuration")

    oauth = setup_oauth()
    if config.ALLOW_LOGOUT_GET_METHOD:
        api("logout")(sign_out)

    return app
