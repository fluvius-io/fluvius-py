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


def get_private_key(config):
    if config.CLIENT_SECRET:
        if config.CLIENT_PRIVATE_KEY or config.CLIENT_PRIVATE_KEY_FILE:
            raise ValueError('[CLIENT_SECRET] is already set. Must not set either [CLIENT_PRIVATE_KEY] or [CLIENT_PRIVATE_KEY_FILE]')

        return None

    if bool(config.CLIENT_PRIVATE_KEY) == bool(config.CLIENT_PRIVATE_KEY_FILE):
        raise ValueError('Only one of the two setting can be set: [CLIENT_PRIVATE_KEY, CLIENT_PRIVATE_KEY_FILE]')

    if config.CLIENT_PRIVATE_KEY:
        return CLIENT_PRIVATE_KEY

    with open(config.CLIENT_PRIVATE_KEY_FILE, "r") as f:
        return f.read()

def setup_authentication(app):
    # Enable Sanic Extensions
    Extend(app)

    # === CONFIG ===
    CLIENT_ID = app.config.KC_CLIENT_ID
    CLIENT_SECRET = app.config.KC_CLIENT_SECRET
    CLIENT_PRIVATE_KEY = get_private_key(app.config)
    REDIRECT_URI = app.config.KC_REDIRECT_URL
    DISCOVERY_URL = f"{app.config.KC_SERVER_URL}/realms/{app.config.KC_REALM}/.well-known/openid-configuration"

    logger.info('CONFIG: %s', app.config)

    async def create_client(app):
        if CLIENT_PRIVATE_KEY is not None:
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
        return oauth_client

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
        return jwt.encode(header, claims, CLIENT_PRIVATE_KEY).decode("utf-8")

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

    # === APP SETUP ===
    @app.before_server_start
    async def setup_oidc(app, _):
        # async with AsyncOAuth2Client() as client:
        #     resp = await client.get(DISCOVERY_URL)
        app.ctx.oidc_config = {'issuer': 'https://id.adaptive-bits.com/auth/realms/dev-1.fluvius.io', 'authorization_endpoint': 'https://id.adaptive-bits.com/auth/realms/dev-1.fluvius.io/protocol/openid-connect/auth', 'token_endpoint': 'https://id.adaptive-bits.com/auth/realms/dev-1.fluvius.io/protocol/openid-connect/token', 'introspection_endpoint': 'https://id.adaptive-bits.com/auth/realms/dev-1.fluvius.io/protocol/openid-connect/token/introspect', 'userinfo_endpoint': 'https://id.adaptive-bits.com/auth/realms/dev-1.fluvius.io/protocol/openid-connect/userinfo', 'end_session_endpoint': 'https://id.adaptive-bits.com/auth/realms/dev-1.fluvius.io/protocol/openid-connect/logout', 'frontchannel_logout_session_supported': True, 'frontchannel_logout_supported': True, 'jwks_uri': 'https://id.adaptive-bits.com/auth/realms/dev-1.fluvius.io/protocol/openid-connect/certs', 'check_session_iframe': 'https://id.adaptive-bits.com/auth/realms/dev-1.fluvius.io/protocol/openid-connect/login-status-iframe.html', 'grant_types_supported': ['authorization_code', 'implicit', 'refresh_token', 'password', 'client_credentials', 'urn:ietf:params:oauth:grant-type:device_code', 'urn:openid:params:grant-type:ciba'], 'acr_values_supported': ['0', '1'], 'response_types_supported': ['code', 'none', 'id_token', 'token', 'id_token token', 'code id_token', 'code token', 'code id_token token'], 'subject_types_supported': ['public', 'pairwise'], 'id_token_signing_alg_values_supported': ['PS384', 'ES384', 'RS384', 'HS256', 'HS512', 'ES256', 'RS256', 'HS384', 'ES512', 'PS256', 'PS512', 'RS512'], 'id_token_encryption_alg_values_supported': ['RSA-OAEP', 'RSA-OAEP-256', 'RSA1_5'], 'id_token_encryption_enc_values_supported': ['A256GCM', 'A192GCM', 'A128GCM', 'A128CBC-HS256', 'A192CBC-HS384', 'A256CBC-HS512'], 'userinfo_signing_alg_values_supported': ['PS384', 'ES384', 'RS384', 'HS256', 'HS512', 'ES256', 'RS256', 'HS384', 'ES512', 'PS256', 'PS512', 'RS512', 'none'], 'userinfo_encryption_alg_values_supported': ['RSA-OAEP', 'RSA-OAEP-256', 'RSA1_5'], 'userinfo_encryption_enc_values_supported': ['A256GCM', 'A192GCM', 'A128GCM', 'A128CBC-HS256', 'A192CBC-HS384', 'A256CBC-HS512'], 'request_object_signing_alg_values_supported': ['PS384', 'ES384', 'RS384', 'HS256', 'HS512', 'ES256', 'RS256', 'HS384', 'ES512', 'PS256', 'PS512', 'RS512', 'none'], 'request_object_encryption_alg_values_supported': ['RSA-OAEP', 'RSA-OAEP-256', 'RSA1_5'], 'request_object_encryption_enc_values_supported': ['A256GCM', 'A192GCM', 'A128GCM', 'A128CBC-HS256', 'A192CBC-HS384', 'A256CBC-HS512'], 'response_modes_supported': ['query', 'fragment', 'form_post', 'query.jwt', 'fragment.jwt', 'form_post.jwt', 'jwt'], 'registration_endpoint': 'https://id.adaptive-bits.com/auth/realms/dev-1.fluvius.io/clients-registrations/openid-connect', 'token_endpoint_auth_methods_supported': ['private_key_jwt', 'client_secret_basic', 'client_secret_post', 'tls_client_auth', 'client_secret_jwt'], 'token_endpoint_auth_signing_alg_values_supported': ['PS384', 'ES384', 'RS384', 'HS256', 'HS512', 'ES256', 'RS256', 'HS384', 'ES512', 'PS256', 'PS512', 'RS512'], 'introspection_endpoint_auth_methods_supported': ['private_key_jwt', 'client_secret_basic', 'client_secret_post', 'tls_client_auth', 'client_secret_jwt'], 'introspection_endpoint_auth_signing_alg_values_supported': ['PS384', 'ES384', 'RS384', 'HS256', 'HS512', 'ES256', 'RS256', 'HS384', 'ES512', 'PS256', 'PS512', 'RS512'], 'authorization_signing_alg_values_supported': ['PS384', 'ES384', 'RS384', 'HS256', 'HS512', 'ES256', 'RS256', 'HS384', 'ES512', 'PS256', 'PS512', 'RS512'], 'authorization_encryption_alg_values_supported': ['RSA-OAEP', 'RSA-OAEP-256', 'RSA1_5'], 'authorization_encryption_enc_values_supported': ['A256GCM', 'A192GCM', 'A128GCM', 'A128CBC-HS256', 'A192CBC-HS384', 'A256CBC-HS512'], 'claims_supported': ['aud', 'sub', 'iss', 'auth_time', 'name', 'given_name', 'family_name', 'preferred_username', 'email', 'acr'], 'claim_types_supported': ['normal'], 'claims_parameter_supported': True, 'scopes_supported': ['openid', 'web-origins', 'roles', 'microprofile-jwt', 'phone', 'profile', 'acr', 'offline_access', 'email', 'address'], 'request_parameter_supported': True, 'request_uri_parameter_supported': True, 'require_request_uri_registration': True, 'code_challenge_methods_supported': ['plain', 'S256'], 'tls_client_certificate_bound_access_tokens': True, 'revocation_endpoint': 'https://id.adaptive-bits.com/auth/realms/dev-1.fluvius.io/protocol/openid-connect/revoke', 'revocation_endpoint_auth_methods_supported': ['private_key_jwt', 'client_secret_basic', 'client_secret_post', 'tls_client_auth', 'client_secret_jwt'], 'revocation_endpoint_auth_signing_alg_values_supported': ['PS384', 'ES384', 'RS384', 'HS256', 'HS512', 'ES256', 'RS256', 'HS384', 'ES512', 'PS256', 'PS512', 'RS512'], 'backchannel_logout_supported': True, 'backchannel_logout_session_supported': True, 'device_authorization_endpoint': 'https://id.adaptive-bits.com/auth/realms/dev-1.fluvius.io/protocol/openid-connect/auth/device', 'backchannel_token_delivery_modes_supported': ['poll', 'ping'], 'backchannel_authentication_endpoint': 'https://id.adaptive-bits.com/auth/realms/dev-1.fluvius.io/protocol/openid-connect/ext/ciba/auth', 'backchannel_authentication_request_signing_alg_values_supported': ['PS384', 'ES384', 'RS384', 'ES256', 'RS256', 'ES512', 'PS256', 'PS512', 'RS512'], 'require_pushed_authorization_requests': False, 'pushed_authorization_request_endpoint': 'https://id.adaptive-bits.com/auth/realms/dev-1.fluvius.io/protocol/openid-connect/ext/par/request', 'mtls_endpoint_aliases': {'token_endpoint': 'https://id.adaptive-bits.com/auth/realms/dev-1.fluvius.io/protocol/openid-connect/token', 'revocation_endpoint': 'https://id.adaptive-bits.com/auth/realms/dev-1.fluvius.io/protocol/openid-connect/revoke', 'introspection_endpoint': 'https://id.adaptive-bits.com/auth/realms/dev-1.fluvius.io/protocol/openid-connect/token/introspect', 'device_authorization_endpoint': 'https://id.adaptive-bits.com/auth/realms/dev-1.fluvius.io/protocol/openid-connect/auth/device', 'registration_endpoint': 'https://id.adaptive-bits.com/auth/realms/dev-1.fluvius.io/clients-registrations/openid-connect', 'userinfo_endpoint': 'https://id.adaptive-bits.com/auth/realms/dev-1.fluvius.io/protocol/openid-connect/userinfo', 'pushed_authorization_request_endpoint': 'https://id.adaptive-bits.com/auth/realms/dev-1.fluvius.io/protocol/openid-connect/ext/par/request', 'backchannel_authentication_endpoint': 'https://id.adaptive-bits.com/auth/realms/dev-1.fluvius.io/protocol/openid-connect/ext/ciba/auth'}}

        # Shared OAuth2 client instance (stateless usage only!)
        app.ctx.oauth_client = await create_client(app)

    @app.route("/auth/login")
    async def login(request):
        client = app.ctx.oauth_client

        uri, state = client.create_authorization_url(
            app.ctx.oidc_config["authorization_endpoint"]
        )

        request.ctx.session['state'] = state
        return response.redirect(uri)

    @app.route("/auth/callback")
    async def auth_callback(request):
        code = request.args.get("code")
        state = request.args.get("state")

        if not code or not state:
            return response.text("Missing code or state", status=400)

        ss = request.ctx.session.get("state")
        if ss != state:
            return response.text(f"State mismatch: {ss} != {state}", status=400)

        if CLIENT_PRIVATE_KEY:
            auth = authenticate_private_key_jwt(code)
        else:
            auth = authenticate_client_secret(code)
        # Save to session
        request.ctx.session["user"] = auth.pop('user')

        return response.json(auth)

    return app
