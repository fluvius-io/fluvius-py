# See: https://docs.authlib.org/en/v1.5.1/client/httpx.html#using-private-key-jwt-in-httpx
from sanic_jwt import Initialize
from .kcauth import bp as keycloak_blueprint
from .kcutil import authenticate, retrieve_user

from .. import config

def setup_authentication(app):
    # Update with custom config if provided
    # Initialize JWT with Keycloak authentication
    jwt = Initialize(
        app,
        authenticate=authenticate,
        retrieve_user=retrieve_user,
        url_prefix="/auth",
        access_token_name="token",
        expiration_delta=config.KC_ACCESS_TOKEN_EXPIRATION,
        cookie_set=True,
        cookie_secure=False,  # Set to True in production with HTTPS
        cookie_httponly=True,
        refresh_token_enabled=True,
    )

    # Register blueprints
    app.blueprint(keycloak_blueprint)

    return app
