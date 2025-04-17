import uuid
import asyncio
from types import SimpleNamespace

from sanic import Sanic, response
from sanic_ext import Extend
from authlib.integrations.httpx_client import AsyncOAuth2Client
from authlib.jose import jwt, JsonWebKey
from datetime import datetime, timedelta

from .. import config, logger

def auth_required(handler):
    @wraps(handler)
    async def decorated(request, *args, **kwargs):
        user = request.ctx.session.get("user")
        app = request.app

        if not user:
            return redirect("/auth/login")

        profile = SimpleNamespace()
        organization = SimpleNamespace()

        context = SimpleNamespace(
            org=organization,
            user=user,
            profile=profile,
            headers=request.headers
        )

        return await handler(request, context, *args, **kwargs)
    return decorated

def setup_authentication(app):
    # Enable Sanic Extensions
    Extend(app)

    # === CONFIG ===
    CLIENT_ID = app.config.KC_CLIENT_ID
    CLIENT_SECRET = app.config.KC_CLIENT_SECRET
    CLIENT_PRIVATE_KEY = app.config.KC_CLIENT_PRIVATE_KEY
    CLIENT_PRIVATE_KEY_FILE = app.config.KC_CLIENT_PRIVATE_KEY_FILE

    REDIRECT_URI = "/auth/callback"
    DISCOVERY_URL = f"{app.config.KC_SERVER_URL}/realms/{app.config.KC_REALM}/.well-known/openid-configuration"

    logger.info('CONFIG: %s', app.config)

    def get_private_key():
        if CLIENT_SECRET:
            if CLIENT_PRIVATE_KEY or CLIENT_PRIVATE_KEY_FILE:
                raise ValueError('[CLIENT_SECRET] is already set. Must not set either [CLIENT_PRIVATE_KEY] or [CLIENT_PRIVATE_KEY_FILE]')

            return None

        if bool(CLIENT_PRIVATE_KEY) == bool(CLIENT_PRIVATE_KEY_FILE):
            raise ValueError('Only one of the two setting can be set: [CLIENT_PRIVATE_KEY, CLIENT_PRIVATE_KEY_FILE]')

        if CLIENT_PRIVATE_KEY:
            return CLIENT_PRIVATE_KEY

        with open(CLIENT_PRIVATE_KEY_FILE, "r") as f:
            return f.read()

    PRIVATE_KEY = get_private_key()

    async def create_client(app):
        if PRIVATE_KEY is not None:
            # Shared OAuth2 client instance (stateless usage only!)
            oauth_client = AsyncOAuth2Client(
                client_id=CLIENT_ID,
                scope="openid profile email",
                redirect_uri=REDIRECT_URI,
            )

            # Preload client_assertion and JWKS
            await refresh_client_assertion(app)
            await get_jwks(app)

            return oauth_client

        oauth_client = AsyncOAuth2Client(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            redirect_uri=REDIRECT_URI,
            scope="openid email profile",
        )

    # === UTILS ===
    def create_client_assertion(issuer: str, audience: str) -> str:
        now = datetime.utcnow()
        claims = {
            "iss": issuer,
            "sub": issuer,
            "aud": audience,
            "jti": str(uuid.uuid4()),
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=5)).timestamp()),
        }
        header = {"alg": "RS256"}
        return jwt.encode(header, claims, PRIVATE_KEY).decode("utf-8")

    async def refresh_client_assertion(app):
        # Called periodically or on startup
        app.ctx.client_assertion = create_client_assertion(
            issuer=CLIENT_ID,
            audience=app.ctx.oidc_config["token_endpoint"]
        )
        app.ctx.client_assertion_exp = datetime.utcnow() + timedelta(minutes=5)

    async def get_valid_client_assertion(app):
        if datetime.utcnow() >= app.ctx.client_assertion_exp:
            await refresh_client_assertion(app)
        return app.ctx.client_assertion

    async def get_jwks(app):
        if not hasattr(app.ctx, "jwks") or datetime.utcnow() >= app.ctx.jwks_exp:
            resp = await app.ctx.oauth_client.get(app.ctx.oidc_config["jwks_uri"])
            app.ctx.jwks = JsonWebKey.import_key_set(resp.json())
            app.ctx.jwks_exp = datetime.utcnow() + timedelta(hours=1)
        return app.ctx.jwks

    # === APP SETUP ===
    @app.before_server_start
    async def setup_oidc(app, _):
        async with AsyncOAuth2Client() as tmp_client:
            resp = await tmp_client.get(DISCOVERY_URL)
            app.ctx.oidc_config = resp.json()

        # Shared OAuth2 client instance (stateless usage only!)
        app.ctx.oauth_client = await create_client(app)

    @app.route("/auth/login")
    async def login(request):
        client = request.ctx.oauth_client

        uri, state = client.create_authorization_url(
            app.ctx.oidc_config["authorization_endpoint"]
        )
        request.ctx.session = {"state": state}
        return response.redirect(uri)

    async def authenticate_private_key_jwt(code):
        client = app.ctx.oauth_client

        client_assertion = await get_valid_client_assertion(app)
        token = await client.fetch_token(
            url=app.ctx.oidc_config["token_endpoint"],
            code=code,
            grant_type="authorization_code",
            client_assertion_type="urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            client_assertion=client_assertion,
        )

        id_token = token.get("id_token")
        if not id_token:
            return response.text("Missing id_token", status=400)

        # Decode and verify ID token using JWKS
        jwks = await get_jwks(app)
        claims = jwt.decode(id_token, jwks, claims_options={
            "iss": {"essential": True, "value": app.ctx.oidc_config["issuer"]},
            "aud": {"essential": True, "value": CLIENT_ID},
            "exp": {"essential": True}
        })

        claims.validate()
        user = {
            "sub": claims["sub"],
            "email": claims.get("email"),
            "name": claims.get("name"),
            "username": claims.get("preferred_username"),
            "roles": claims.get("realm_access", {}).get("roles", [])
        }

        return {
            "access_token": token["access_token"],
            "id_token": id_token,
            "claims_from_id_token": claims,
            "user": user
        }

    async def authenticate_client_secret(code):
        token = await client.fetch_token(
            app.ctx.oidc_config["token_endpoint"],
            code=code,
            authorization_response=str(request.url),
        )

        userinfo_resp = await client.get(app.ctx.oidc_config["userinfo_endpoint"])
        user = userinfo_resp.json()

        return {
            "id_token": token.get("id_token"),
            "access_token": token.get("access_token"),
            "user": user
        }

    @app.route("/auth/callback")
    async def auth_callback(request):
        code = request.args.get("code")
        state = request.args.get("state")

        if not code or not state:
            return response.text("Missing code or state", status=400)

        if request.ctx.session.get("state") != state:
            return response.text("State mismatch", status=400)

        if PRIVATE_KEY:
            auth = authenticate_private_key_jwt(code)
        else:
            auth = authenticate_client_secret(code)
        # Save to session
        request.ctx.session["user"] = auth.pop('user')

        return response.json(auth)

    return app
