import json
import time
import requests
from jose import jwt
from urllib.parse import urlencode

from .config import (
    KEYCLOAK_SERVER_URL,
    KEYCLOAK_REALM,
    KEYCLOAK_CLIENT_ID,
    KEYCLOAK_CLIENT_SECRET,
    JWT_ALGORITHM,
    AUTH_REDIRECT_URI,
    JWKS_CACHE_TTL
)

# Cache for JWKS
_jwks_cache = None
_jwks_last_updated = 0

class KeycloakError(Exception):
    """Keycloak client error"""
    pass

def get_openid_configuration():
    """Get the OpenID Connect configuration from Keycloak"""
    url = f"{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM}/.well-known/openid-configuration"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise KeycloakError(f"Failed to get OpenID configuration: {str(e)}")

def get_jwks():
    """Get the JSON Web Key Set from Keycloak"""
    global _jwks_cache, _jwks_last_updated
    current_time = time.time()
    
    # Use cached JWKS if available and not expired
    if _jwks_cache and current_time - _jwks_last_updated < JWKS_CACHE_TTL:
        return _jwks_cache
    
    # Get OpenID configuration
    config = get_openid_configuration()
    jwks_uri = config.get("jwks_uri")
    if not jwks_uri:
        raise KeycloakError("JWKS URI not found in OpenID configuration")
    
    # Get JWKS
    try:
        response = requests.get(jwks_uri)
        response.raise_for_status()
        _jwks_cache = response.json()
        _jwks_last_updated = current_time
        return _jwks_cache
    except Exception as e:
        raise KeycloakError(f"Failed to get JWKS: {str(e)}")

def get_authorization_url(state=None, scope="openid profile email"):
    """Get authorization URL for OAuth2 flow"""
    config = get_openid_configuration()
    auth_endpoint = config.get("authorization_endpoint")
    if not auth_endpoint:
        raise KeycloakError("Authorization endpoint not found in OpenID configuration")
    
    params = {
        "client_id": KEYCLOAK_CLIENT_ID,
        "redirect_uri": AUTH_REDIRECT_URI,
        "response_type": "code",
        "scope": scope
    }
    
    if state:
        params["state"] = state
    
    return f"{auth_endpoint}?{urlencode(params)}"

def get_token_from_code(code):
    """Exchange authorization code for token in OAuth2 flow"""
    config = get_openid_configuration()
    token_endpoint = config.get("token_endpoint")
    if not token_endpoint:
        raise KeycloakError("Token endpoint not found in OpenID configuration")
    
    data = {
        "client_id": KEYCLOAK_CLIENT_ID,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": AUTH_REDIRECT_URI
    }
    
    if KEYCLOAK_CLIENT_SECRET:
        data["client_secret"] = KEYCLOAK_CLIENT_SECRET
    
    try:
        response = requests.post(token_endpoint, data=data)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise KeycloakError(f"Failed to exchange code for token: {str(e)}")

def get_token_from_credentials(username, password):
    """Get token from username and password"""
    config = get_openid_configuration()
    token_endpoint = config.get("token_endpoint")
    if not token_endpoint:
        raise KeycloakError("Token endpoint not found in OpenID configuration")
    
    data = {
        "client_id": KEYCLOAK_CLIENT_ID,
        "grant_type": "password",
        "username": username,
        "password": password
    }
    
    if KEYCLOAK_CLIENT_SECRET:
        data["client_secret"] = KEYCLOAK_CLIENT_SECRET
    
    try:
        response = requests.post(token_endpoint, data=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            raise KeycloakError("Invalid username or password")
        else:
            raise KeycloakError(f"Authentication failed: {str(e)}")
    except Exception as e:
        raise KeycloakError(f"Authentication failed: {str(e)}")

def refresh_token(refresh_token):
    """Refresh an access token"""
    config = get_openid_configuration()
    token_endpoint = config.get("token_endpoint")
    if not token_endpoint:
        raise KeycloakError("Token endpoint not found in OpenID configuration")
    
    data = {
        "client_id": KEYCLOAK_CLIENT_ID,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }
    
    if KEYCLOAK_CLIENT_SECRET:
        data["client_secret"] = KEYCLOAK_CLIENT_SECRET
    
    try:
        response = requests.post(token_endpoint, data=data)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise KeycloakError(f"Failed to refresh token: {str(e)}")

def logout(refresh_token):
    """Logout from Keycloak"""
    config = get_openid_configuration()
    logout_endpoint = config.get("end_session_endpoint")
    if not logout_endpoint:
        raise KeycloakError("Logout endpoint not found in OpenID configuration")
    
    # Revoke the refresh token if possible
    try:
        revoke_endpoint = f"{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/revoke"
        data = {
            "client_id": KEYCLOAK_CLIENT_ID,
            "token": refresh_token,
            "token_type_hint": "refresh_token"
        }
        
        if KEYCLOAK_CLIENT_SECRET:
            data["client_secret"] = KEYCLOAK_CLIENT_SECRET
            
        requests.post(revoke_endpoint, data=data)
    except Exception:
        pass  # Ignore any errors during revocation
    
    # Return logout URL
    params = {"redirect_uri": AUTH_REDIRECT_URI.rsplit("/", 1)[0]}
    return f"{logout_endpoint}?{urlencode(params)}"

def get_userinfo(access_token):
    """Get user info from Keycloak"""
    config = get_openid_configuration()
    userinfo_endpoint = config.get("userinfo_endpoint")
    if not userinfo_endpoint:
        raise KeycloakError("Userinfo endpoint not found in OpenID configuration")
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        response = requests.get(userinfo_endpoint, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise KeycloakError(f"Failed to get user info: {str(e)}")

def verify_token(token):
    """Verify and decode a JWT token"""
    if not token:
        raise KeycloakError("No token provided")
    
    try:
        # Get the JWKS for token verification
        jwks = get_jwks()
        
        # Get the header without verification
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        if not kid:
            raise KeycloakError("No key ID found in token header")
        
        # Find the matching key in JWKS
        rsa_key = None
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                rsa_key = key
                break
        
        if not rsa_key:
            raise KeycloakError(f"No matching key found in JWKS for kid: {kid}")
        
        # Verify the token
        algorithm = header.get("alg", JWT_ALGORITHM)
        issuer = f"{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM}"
        
        decoded = jwt.decode(
            token,
            rsa_key,
            algorithms=[algorithm],
            audience=KEYCLOAK_CLIENT_ID,
            issuer=issuer
        )
        
        return decoded
    except jwt.ExpiredSignatureError:
        raise KeycloakError("Token has expired")
    except jwt.JWTClaimsError as e:
        raise KeycloakError(f"Invalid claims in token: {str(e)}")
    except jwt.JWTError as e:
        raise KeycloakError(f"Invalid token: {str(e)}")
    except Exception as e:
        raise KeycloakError(f"Failed to validate token: {str(e)}")