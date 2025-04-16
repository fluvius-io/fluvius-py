import json
import requests
from jose import jwt
from sanic_jwt.exceptions import AuthenticationFailed

from .. import config


# Cache for JWKS
_jwks_cache = None
_jwks_last_updated = 0

def get_keycloak_openid_configuration():
    """Get OpenID configuration from Keycloak"""
    url = f"{config.KC_SERVER_URL}/realms/{config.KC_REALM}/.well-known/openid-configuration"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise AuthenticationFailed(f"Failed to get OpenID configuration: {str(e)}")


def get_jwks():
    """Get the JSON Web Key Set from Keycloak"""
    global _jwks_cache, _jwks_last_updated
    import time
    current_time = time.time()

    # Use cached JWKS if available and less than 1 hour old
    if _jwks_cache and current_time - _jwks_last_updated < 3600:
        return _jwks_cache

    config = get_keycloak_openid_configuration()
    jwks_uri = config.get("jwks_uri")
    if not jwks_uri:
        raise AuthenticationFailed("JWKS URI not found in OpenID configuration")

    try:
        response = requests.get(jwks_uri)
        response.raise_for_status()
        _jwks_cache = response.json()
        _jwks_last_updated = current_time
        return _jwks_cache
    except Exception as e:
        raise AuthenticationFailed(f"Failed to get JWKS: {str(e)}")


async def authenticate(request, *args, **kwargs):
    """Authenticate a user with Keycloak credentials and return an access token"""
    if not request.json:
        raise AuthenticationFailed("Missing JSON request body")

    username = request.json.get("username", "")
    password = request.json.get("password", "")

    if not username or not password:
        raise AuthenticationFailed("Missing username or password")

    # Get token from Keycloak
    token_url = f"{config.KC_SERVER_URL}/realms/{config.KC_REALM}/protocol/openid-connect/token"
    data = {
        "client_id": config.KC_CLIENT_ID,
        "grant_type": "password",
        "username": username,
        "password": password
    }

    # Add client secret if available
    if KEYCLOAK_CONFIG.get("client_secret"):
        data["client_secret"] = config.KC_CLIENT_SECRET

    try:
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        token_data = response.json()

        # Decode the token to get user info
        access_token = token_data.get("access_token")
        if not access_token:
            raise AuthenticationFailed("No access token in response")

        # Parse token without verification (we'll verify it in retrieve_user)
        # This is just to get the user_id and other claims
        try:
            payload = jwt.get_unverified_claims(access_token)
            return {
                "user_id": payload.get("sub"),
                "access_token": access_token,
                "refresh_token": token_data.get("refresh_token"),
                "username": payload.get("preferred_username", username),
                "realm_roles": payload.get("realm_access", {}).get("roles", [])
            }
        except Exception as e:
            raise AuthenticationFailed(f"Failed to parse access token: {str(e)}")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            raise AuthenticationFailed("Invalid username or password")
        else:
            raise AuthenticationFailed(f"Authentication failed: {str(e)}")
    except Exception as e:
        raise AuthenticationFailed(f"Authentication failed: {str(e)}")


async def retrieve_user(request, payload, *args, **kwargs):
    """Verify the JWT token and retrieve user from payload"""
    if not payload:
        return None

    token = payload.get("access_token")
    if not token:
        return None

    try:
        # Get JWKS for token verification
        jwks = get_jwks()

        # Verify and decode the token
        header = jwt.get_unverified_header(token)
        rsa_key = None

        # Find the matching key in JWKS
        for key in jwks.get("keys", []):
            if key.get("kid") == header.get("kid"):
                rsa_key = key
                break

        if not rsa_key:
            raise AuthenticationFailed("No matching key found in JWKS")

        # Get the algorithm from the header or use RS256 as default
        algorithm = header.get("alg", "RS256")

        # Verify the token
        issuer = f"{config.KC_SERVER_URL}/realms/{config.KC_REALM}"
        decoded = jwt.decode(
            token,
            rsa_key,
            algorithms=[algorithm],
            audience=config.KC_CLIENT_ID,
            issuer=issuer
        )

        # Return the user information
        return {
            "user_id": decoded.get("sub"),
            "username": decoded.get("preferred_username"),
            "email": decoded.get("email"),
            "realm_roles": decoded.get("realm_access", {}).get("roles", []),
            "resource_access": decoded.get("resource_access", {})
        }
    except jwt.ExpiredSignatureError:
        raise AuthenticationFailed("Token has expired")
    except jwt.JWTClaimsError:
        raise AuthenticationFailed("Invalid claims in token")
    except jwt.JWTError:
        raise AuthenticationFailed("Invalid token")
    except Exception as e:
        raise AuthenticationFailed(f"Failed to validate token: {str(e)}")
