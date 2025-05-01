import base64
import httpx
import json

from types import SimpleNamespace
from functools import wraps
from authlib.integrations.starlette_client import OAuth
from authlib.jose import jwt, JsonWebKey
from authlib.jose.util import extract_header
from fastapi import Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from .setup import on_startup
from .helper import uri

from . import config, logger

IDEMPOTENCY_KEY = config.RESP_HEADER_IDEMPOTENCY


def auth_required(inject_ctx=True, **kwargs):
    def decorator(endpoint):
        @wraps(endpoint)
        async def wrapper(request: Request, *args, **kwargs):
            if not getattr(request.state, 'auth_context', None):
                raise HTTPException(status_code=401, detail="Not authenticated.")

            return await endpoint(request, *args, **kwargs)

        return wrapper
    return decorator


class FluviusAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, auth_provider=None):
        super().__init__(app)
        self._auth_provider = FluviusAuthProfileProvider.get(auth_provider)

    def get_auth_context(self, request):
        # You can optionally decode and validate the token here
        if not (id_token := request.cookies.get("id_token")):
            return None

        try:
            user = request.session.get("user")
            if not user:
                return None
        except (KeyError, ValueError):
            return None

        auth = self._auth_provider(user)

        return SimpleNamespace(
            token = id_token,
            user = auth.user,
            profile = auth.profile,
            organization = auth.organization,
            sysroles = auth.system_roles
        )

    async def dispatch(self, request: Request, call_next):
        try:
            request.state.auth_context = self.get_auth_context(request)
        except Exception as e:
            logger.exception(e)
            raise

        response = await call_next(request)

        if idem_key := request.headers.get(IDEMPOTENCY_KEY):
            response.headers[IDEMPOTENCY_KEY] = idem_key

        return response



class FluviusAuthProfileProvider(object):
    REGISTRY = {}

    def __init_subclass__(cls, key):
        if key in FluviusAuthProfileProvider.REGISTRY:
            raise ValueError(f'Auth Profile Provider is already registered: {key} => {FluviusAuthProfileProvider.REGISTRY[key]}')

        FluviusAuthProfileProvider.REGISTRY[key] = cls

    @classmethod
    def get(cls, key):
        if key is None:
            return FluviusAuthProfileProvider

        return FluviusAuthProfileProvider.REGISTRY[key]

    """ Lookup services for user related info """
    def __init__(self, user):
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated.")

        self._user = user
        self._profile = SimpleNamespace()
        self._organization = SimpleNamespace()
        self._sysroles = ('user', 'sysadmin', 'operator')


    @property
    def user(self):
        return self._user

    @property
    def profile(self):
        return self._profile

    @property
    def organization(self):
        return self._organization

    @property
    def system_roles(self):
        return self._sysroles


def setup_authentication(app, config=config, base_path="/auth"):
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
            redirect_uri=config.DEFAULT_REDIRECT_URI,
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

    def extract_jwt_kid(token: str) -> dict:
        header_segment = token.split('.')[0]
        padded = header_segment + '=' * (-len(header_segment) % 4)
        decoded = base64.urlsafe_b64decode(padded)
        return json.loads(decoded)['kid']

    async def decode_id_token(jwks_keyset, id_token: str):
        # This will parse the JWT and extract both the header and payload
        kid = extract_jwt_kid(id_token)

        # 🔍 Find the correct key by kid
        try:
            key = next(k for k in jwks_keyset.keys if k.kid == kid)
        except StopIteration:
            raise HTTPException(status_code=401, detail="Public key not found for kid")

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
        return await oauth.keycloak.authorize_redirect(request, config.DEFAULT_REDIRECT_URI)

    @api("callback")
    async def oauth_callback(request: Request):
        token = await oauth.keycloak.authorize_access_token(request)
        id_token = token.get("id_token")
        if not id_token:
            raise HTTPException(status_code=400, detail="Missing ID token")

        user = await decode_id_token(request.app.state.jwks_keyset, id_token)
        request.session["user"] = user
        response = RedirectResponse(url="/auth/verify")
        response.set_cookie('id_token', id_token)
        return response

    @api("verify")
    @auth_required()
    async def verify_auth(request: Request):
        if not (user := request.state.auth_context.user):
            raise HTTPException(status_code=401, detail=f"Not logged in: {user}")

        return {
            "message": f"OK",
            "context": request.state.auth_context,
            "headers": dict(request.headers)
        }

    @api("logout")
    async def logout(request: Request):
        ''' Log out user locally (only for this API) '''
        request.session.clear()
        return {"message": "Logged out"}


    @api("signoff", method=app.post)
    async def sign_off(request: Request):
        ''' Log out user globally (including Keycloak) '''
        # 2. Logout from Keycloak using the logout endpoint
        access_token = request.cookies.get("id_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="No access token found")

        request.session.clear()
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
        response = RedirectResponse(url=LOGOUT_REDIRECT_URI)  # Redirect after logout
        response.delete_cookie("id_token")  # Clear the access_token cookie

        return response

    # === Keycloak Configuration ===
    LOGOUT_REDIRECT_URI = "/auth/verify"
    KEYCLOAK_ISSUER = uri(config.KEYCLOAK_BASE_URL, "realms", config.KEYCLOAK_REALM)
    KEYCLOAK_JWKS_URI = uri(KEYCLOAK_ISSUER, "protocol/openid-connect/certs")
    KEYCLOAK_LOGOUT_URI = uri(KEYCLOAK_ISSUER, "protocol/openid-connect/logout")
    KEYCLOAK_METADATA_URI = uri(KEYCLOAK_ISSUER, ".well-known/openid-configuration")

    oauth = _setup_oauth()
    return app
