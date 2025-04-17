import base64
import json

from types import SimpleNamespace
from functools import wraps
from authlib.integrations.starlette_client import OAuth
from authlib.jose import jwt, JsonWebKey
from authlib.jose.util import extract_header
from fastapi import Request, Depends, HTTPException
from fastapi.responses import RedirectResponse

import httpx

from . import config, logger


def auth_required(inject_ctx=True):
    def decorator(endpoint):
        @wraps(endpoint)
        async def wrapper(request: Request, *args, **kwargs):
            # You can optionally decode and validate the token here
            if not (id_token := request.cookies.get("id_token")):
                raise HTTPException(status_code=401, detail="Not authenticated.")

            try:
                user = request.session.get("user")
                if not user:
                    raise ValueError()
            except (KeyError, ValueError):
                raise HTTPException(status_code=401, detail="User logged out.")

            request.state.auth = SimpleNamespace(
                user = user,
                token = id_token
            )

            return await endpoint(request, *args, **kwargs)

        return wrapper
    return decorator

def setup_authentication(app, config=config):
    DEFAULT_REDIRECT_URI = config.DEFAULT_REDIRECT_URI

    # === Keycloak Configuration ===
    KEYCLOAK_BASE_URL = config.KEYCLOAK_BASE_URL
    KEYCLOAK_REALM = config.KEYCLOAK_REALM
    KEYCLOAK_CLIENT_ID = config.KEYCLOAK_CLIENT_ID
    KEYCLOAK_CLIENT_SECRET = config.KEYCLOAK_CLIENT_SECRET
    KEYCLOAK_ISSUER = f"{KEYCLOAK_BASE_URL}/realms/{KEYCLOAK_REALM}"
    KEYCLOAK_JWKS_URI = f"{KEYCLOAK_ISSUER}/protocol/openid-connect/certs"
    KEYCLOAK_LOGOUT_URI = f"{KEYCLOAK_BASE_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/logout"


    # === OAuth Setup ===
    oauth = OAuth()
    oauth.register(
        name='keycloak',
        server_metadata_url=f"{KEYCLOAK_ISSUER}/.well-known/openid-configuration",
        client_id=KEYCLOAK_CLIENT_ID,
        client_secret=KEYCLOAK_CLIENT_SECRET,
        client_kwargs={"scope": "openid profile email"},
        redirect_uri=DEFAULT_REDIRECT_URI,
    )

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
                "aud": {"essential": True, "value": KEYCLOAK_CLIENT_ID},
                "exp": {"essential": True},
            }
        )

        claims.validate()

        return claims

    # Async code at server startup
    @app.on_event("startup")
    async def fetch_jwks_on_startup():
        async with httpx.AsyncClient() as client:
            response = await client.get(KEYCLOAK_JWKS_URI)
            data = response.json()

        app.state.jwks_keyset = JsonWebKey.import_key_set(data)  # Store JWKS in app state

    # === Routes ===
    @app.get("/auth")
    async def home():
        return {"message": "Go to /login to start OAuth2 login with Keycloak"}

    @app.get("/auth/login")
    async def login(request: Request):
        return await oauth.keycloak.authorize_redirect(request, DEFAULT_REDIRECT_URI)

    @app.get("/auth/callback")
    async def auth_callback(request: Request):
        token = await oauth.keycloak.authorize_access_token(request)
        id_token = token.get("id_token")
        if not id_token:
            raise HTTPException(status_code=400, detail="Missing ID token")

        user = await decode_id_token(request.app.state.jwks_keyset, id_token)
        request.session["user"] = user
        response = RedirectResponse(url="/auth/verify")
        response.set_cookie('id_token', id_token)
        return response

    @app.get("/auth/verify")
    @auth_required()
    async def protected(request: Request):
        if not (user := request.state.auth.user):
            raise HTTPException(status_code=401, detail=f"Not logged in: {user}")

        return {
            "message": f"Hello {user.get('preferred_username')}",
            "user": user
        }

    @app.get("/auth/logout")
    async def logout(request: Request):
        request.session.clear()
        return {"message": "Logged out"}


    @app.get("/auth/signoff")
    async def signoff(request: Request):
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
        response = RedirectResponse(url="/auth/verify")  # Redirect after logout
        response.delete_cookie("id_token")  # Clear the access_token cookie

        return response

    return app
