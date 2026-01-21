import base64
import httpx
import json
import secrets

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


from fluvius.error import UnauthorizedError, FluviusException, BadRequestError, config as errconf
from fluvius.data import DataModel
from fluvius.auth import (
    AuthorizationContext, 
    KeycloakTokenPayload, 
    SessionProfile, 
    SessionOrganization, event as auth_event, helper as auth_helper)
from fluvius.helper import when
from pipe import Pipe
from typing import Optional, Awaitable, Callable

from . import config, logger
from .setup import on_startup
from .helper import uri, generate_client_token, generate_session_id, validate_direct_url
from fluvius.error import DEVELOPER_MODE

IDEMPOTENCY_KEY = config.RESP_HEADER_IDEMPOTENCY
DEVELOPER_MODE = errconf.DEVELOPER_MODE
CSRF_TOKEN_LENGTH = 32


def generate_csrf_token() -> str:
    """Generate a cryptographically secure CSRF token"""
    return secrets.token_urlsafe(CSRF_TOKEN_LENGTH)


def validate_csrf_token(request: Request, token: str) -> bool:
    """Validate CSRF token from request against session"""
    session_token = request.session.get('csrf_token')
    if not session_token or not token:
        return False
    # Use constant-time comparison to prevent timing attacks
    return secrets.compare_digest(session_token, token)


def auth_required(inject_ctx=False, **auth_kwargs):
    def decorator(endpoint):
        @wraps(endpoint)
        async def wrapper(request: Request, *args, **kwargs):
            try:
                auth_context = await request.app.state.get_auth_context(request, **auth_kwargs)
            except FluviusException as e:
                # Handle FluviusException directly in middleware to ensure proper status codes
                # Exceptions raised in middleware may not always be caught by FastAPI's exception handlers
                content = e.content

                # Log full error server-side but never expose to client
                if DEVELOPER_MODE:
                    import traceback
                    logger.error(f"Auth error: {e}\n{traceback.format_exc()}")
                    # Still don't expose traceback to client even in dev mode for security

                return JSONResponse(
                    status_code=e.status_code,
                    content=content
                )
            except Exception as e:
                # Always log server-side
                logger.exception(f"Unexpected auth error: {e}")

                return JSONResponse(
                    status_code=500,
                    content={"errcode": "S00.501", "message": "Unexpected auth error: {e}"}
                )

            if inject_ctx:
                return await endpoint(request, auth_context, *args, **kwargs)

            if not auth_context:
                return JSONResponse(
                    status_code=401,
                    content={"errcode": "S00.401", "message": "User is not authenticated"}
                )

            request.state.auth_context = auth_context
            return await endpoint(request, *args, **kwargs)

        return wrapper
    return decorator


class FluviusAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        response = await call_next(request)

        if idem_key := request.headers.get(IDEMPOTENCY_KEY):
            response.headers[IDEMPOTENCY_KEY] = idem_key

        return response


class FluviusAuthProfileProvider(object):
    """ Lookup services for user related info """

    _REGISTRY = {}

    def __init_subclass__(cls):
        super().__init_subclass__()

        key = cls.__name__
        if key in FluviusAuthProfileProvider._REGISTRY:
            raise BadRequestError('S00.002', f'Auth Profile Provider is already registered: {key} => {FluviusAuthProfileProvider._REGISTRY[key]}')

        FluviusAuthProfileProvider._REGISTRY[key] = cls

        if DEVELOPER_MODE:
            logger.info('Registered Auth Profile Provider: %s', cls.__name__)


    def __init__(self, app):
        self._app = app

    @property
    def app(self):
        return self._app

    @classmethod
    def get(cls, key):
        if key is None:
            return FluviusAuthProfileProvider

        try:
            return FluviusAuthProfileProvider._REGISTRY[key]
        except KeyError:
            raise BadRequestError('S00.003', f'Auth Profile Provider is not valid: {key}. Available: {list(FluviusAuthProfileProvider._REGISTRY.keys())}')

    def authorize_claims(self, claims_token: dict) -> KeycloakTokenPayload:
        return KeycloakTokenPayload(**claims_token)

    def get_auth_token(self, request: Request) -> Optional[str]:
        # You can optionally decode and validate the token here
        if not (id_token := request.cookies.get("id_token")):
            return None

        return request.session.get("user")

    async def get_auth_context(self, request: Request, **kwargs) -> Optional[AuthorizationContext]:
        try:
            auth_token = self.get_auth_token(request)
            if not auth_token:
                return None
            auth_user = self.authorize_claims(auth_token)
        except (KeyError, ValueError):
            raise UnauthorizedError("S00.004", "Authorization Failed: Missing or invalid claims token")

        auth_context = await self.setup_context(auth_user)
        return auth_context

    async def setup_context(self, auth_user: KeycloakTokenPayload) -> AuthorizationContext:
        # Extract roles from Keycloak token claims
        realm_roles = auth_user.realm_access.get('roles', []) if auth_user.realm_access else []

        # Extract client-specific roles if needed
        client_roles = []
        if auth_user.resource_access:
            for client, access in auth_user.resource_access.items():
                client_roles.extend(access.get('roles', []))

        # Combine all roles
        all_roles = tuple(set(realm_roles + client_roles))

        profile = SessionProfile(
            id=auth_user.jti,
            name=auth_user.name,
            family_name=auth_user.family_name,
            given_name=auth_user.given_name,
            email=auth_user.email,
            username=auth_user.preferred_username,
            roles=all_roles,
            org_id=auth_user.sub,
            usr_id=auth_user.sid
        )

        organization = SessionOrganization(
            id=auth_user.sub,
            name=auth_user.family_name
        )

        # Extract IAM roles from realm roles (filter for admin/operator roles)
        iamroles = tuple(role for role in realm_roles if role in ('sysadmin', 'operator', 'admin'))

        # Extract realm from token issuer or use a default
        realm = getattr(auth_user, 'iss', '').split('/realms/')[-1] if hasattr(auth_user, 'iss') else 'default'

        return AuthorizationContext(
            realm = realm,
            user = auth_user,
            profile = profile,
            organization = organization,
            iamroles = iamroles
        )

@Pipe
def configure_authentication(app, config=config, base_path="/auth", auth_profile_provider=config.AUTH_PROFILE_PROVIDER):
    # === Keycloak Configuration ===

    KEYCLOAK_CLIENT_ID = config.KEYCLOAK_CLIENT_ID
    KEYCLOAK_CLIENT_SECRET = config.KEYCLOAK_CLIENT_SECRET
    KEYCLOAK_ISSUER = uri(config.KEYCLOAK_BASE_URL, "realms", config.KEYCLOAK_REALM)
    KEYCLOAK_JWKS_URI = uri(KEYCLOAK_ISSUER, "protocol/openid-connect/certs")
    KEYCLOAK_LOGOUT_URI = uri(KEYCLOAK_ISSUER, "protocol/openid-connect/logout")
    KEYCLOAK_SIGNUP_URI = uri(KEYCLOAK_ISSUER, "protocol/openid-connect/registrations")
    KEYCLOAK_METADATA_URI = uri(KEYCLOAK_ISSUER, ".well-known/openid-configuration")
    DEFAULT_CALLBACK_URI = config.DEFAULT_CALLBACK_URI

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
            client_id=KEYCLOAK_CLIENT_ID,
            client_secret=KEYCLOAK_CLIENT_SECRET,
            client_kwargs={"scope": "openid profile email"},
            redirect_uri=DEFAULT_CALLBACK_URI,
        )
        app.add_middleware(FluviusAuthMiddleware)
        app.add_middleware(
            SessionMiddleware,
            secret_key=config.APPLICATION_SECRET_KEY,
            session_cookie=config.SESSION_COOKIE,
            https_only=config.COOKIE_HTTPS_ONLY,
            same_site=config.COOKIE_SAME_SITE_POLICY
        )

        return oauth


    # Async code at server startup
    @on_startup
    async def fetch_jwks_keyset_on_startup(app):
        async with httpx.AsyncClient() as client:
            response = await client.get(KEYCLOAK_JWKS_URI)
            data = response.json()

        app.state.jwks_keyset = JsonWebKey.import_key_set(data)  # Store JWKS in app state

    @on_startup
    async def setup_auth_profile_provider(app):
        if isinstance(auth_profile_provider, str):
            provider_cls = FluviusAuthProfileProvider.get(auth_profile_provider)
        elif issubclass(auth_profile_provider, FluviusAuthProfileProvider):
            provider_cls = auth_profile_provider
        else:
            raise BadRequestError('S00.001', f'Invalid Auth Profile Provider: {auth_profile_provider}')

        app.state.get_auth_context = provider_cls(app).get_auth_context


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

        id_data = await auth_helper.decode_id_token(request.app.state.jwks_keyset, id_token, KEYCLOAK_ISSUER, KEYCLOAK_CLIENT_ID)
        ac_data = await auth_helper.decode_ac_token(request.app.state.jwks_keyset, ac_token)

        id_data.update(
            realm_access=ac_data.get("realm_access"),
            resource_access=ac_data.get("resource_access"),
            client_token=generate_client_token(request.session),
            session_id=generate_session_id(request.session)
        )

        # Regenerate session to prevent session fixation
        old_data = dict(request.session)
        request.session.clear()
        request.session.update(old_data)

        request.session[config.SES_USER_FIELD] = id_data
        next_url = validate_direct_url(request.session.get("next"), config.DEFAULT_SIGNIN_REDIRECT_URI)
        response = RedirectResponse(url=next_url)

        # Set secure cookie flags
        response.set_cookie(
            config.SES_ID_TOKEN_FIELD,
            id_token,
            httponly=True,
            secure=config.COOKIE_HTTPS_ONLY,
            samesite=config.COOKIE_SAME_SITE_POLICY
        )
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

    @api("csrf-token")
    async def get_csrf_token(request: Request):
        """Get or generate CSRF token for the current session"""
        if 'csrf_token' not in request.session:
            request.session['csrf_token'] = generate_csrf_token()
        return {"csrf_token": request.session['csrf_token']}

    @api("sign-in")
    async def sign_in(request: Request):
        # Generate and store CSRF token
        csrf_token = generate_csrf_token()
        request.session['csrf_token'] = csrf_token
        request.session["next"] = request.query_params.get('next')
        callback_uri = validate_direct_url(request.query_params.get('callback'), config.DEFAULT_CALLBACK_URI)
        return await oauth.keycloak.authorize_redirect(request, callback_uri)

    @api("sign-up")
    async def sign_up(request: Request):
        return RedirectResponse(url=KEYCLOAK_SIGNUP_URI)

    @api("sign-out", method=app.post)
    async def sign_out(request: Request):
        """ Log out user globally (including Keycloak) """

        # Validate CSRF token for POST requests
        form_data = await request.form()
        csrf_token = form_data.get('csrf_token') or request.headers.get('X-CSRF-Token')
        if not validate_csrf_token(request, csrf_token):
            raise HTTPException(status_code=403, detail="Invalid CSRF token")

        redirect_uri = validate_direct_url(
            form_data.get('redirect_uri') or request.query_params.get('redirect_uri'),
            config.DEFAULT_LOGOUT_REDIRECT_URI
        )
        
        id_data = request.session.get(config.SES_USER_FIELD)
        id_token = request.cookies.get(config.SES_ID_TOKEN_FIELD)

        # Only proceed with logout if we have a valid session
        if id_token and id_data:
            keycloak_logout_url = f"{KEYCLOAK_LOGOUT_URI}?{urlencode({'id_token_hint': id_token, 'post_logout_redirect_uri': redirect_uri})}"
        else:
            # No valid session, just redirect
            keycloak_logout_url = redirect_uri

        request.session.clear()
        response = RedirectResponse(url=keycloak_logout_url)
        response.delete_cookie(
            config.SES_ID_TOKEN_FIELD,
            httponly=True,
            secure=config.COOKIE_HTTPS_ONLY,
            samesite=config.COOKIE_SAME_SITE_POLICY
        )

        if id_data:
            auth_event.user_logout.send(request, user=id_data)

        return response

    if config.ALLOW_LOGOUT_GET_METHOD:
        api("logout")(sign_out)

    oauth = setup_oauth()

    return app
