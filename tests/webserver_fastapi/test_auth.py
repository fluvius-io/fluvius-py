import pytest
import json
import base64
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from fastapi import FastAPI
from fluvius.fastapi import create_app, setup_authentication


def create_mock_id_token(payload, kid="test-key-id"):
    """Create a mock JWT token with the given payload."""
    # Create a simple mock header
    header = {
        "alg": "RS256",
        "typ": "JWT",
        "kid": kid
    }
    
    # Encode header and payload
    header_json = json.dumps(header).encode()
    header_b64 = base64.urlsafe_b64encode(header_json).decode().rstrip("=")
    
    payload_json = json.dumps(payload).encode()
    payload_b64 = base64.urlsafe_b64encode(payload_json).decode().rstrip("=")
    
    # For testing, we don't need a valid signature
    signature = "mock_signature"
    
    # Combine to form the token
    token = f"{header_b64}.{payload_b64}.{signature}"
    return token


@pytest.fixture
def auth_app(mock_keycloak_config, mock_jwks_keyset):
    """Create a FastAPI app with authentication setup for testing."""
    app = FastAPI()
    
    # Mock the JWKS keyset
    with patch("authlib.jose.JsonWebKey.import_key_set") as mock_import:
        mock_keyset = MagicMock()
        mock_key = MagicMock()
        mock_key.kid = "test-key-id"
        mock_keyset.keys = [mock_key]
        mock_import.return_value = mock_keyset
        
        # Setup authentication
        app = setup_authentication(app)
        
        # Mock httpx client for JWKS fetching
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_jwks_keyset
            mock_response.status_code = 200
            
            mock_client_instance = MagicMock()
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.get.return_value = mock_response
            
            mock_client.return_value = mock_client_instance
            
            # Trigger startup event manually
            for event_handler in app.router.on_startup:
                yield app


@pytest.fixture
def auth_client(auth_app):
    """Create a test client for the auth_app."""
    return TestClient(auth_app)


def test_auth_home_endpoint(auth_client):
    """Test the /auth endpoint returns expected message."""
    response = auth_client.get("/auth")
    assert response.status_code == 200
    assert "login" in response.json()["message"]


def test_auth_login_redirect(auth_client):
    """Test that /auth/login redirects to Keycloak."""
    with patch("authlib.integrations.starlette_client.OAuth.keycloak") as mock_keycloak:
        mock_keycloak.authorize_redirect = MagicMock()
        mock_keycloak.authorize_redirect.return_value = {"redirect": "to_keycloak"}
        
        response = auth_client.get("/auth/login", allow_redirects=False)
        assert response.status_code in (302, 307)  # Redirect status codes


@patch("authlib.jose.jwt.decode")
@patch("authlib.integrations.starlette_client.OAuth.keycloak")
def test_auth_callback(mock_keycloak, mock_jwt_decode, auth_client):
    """Test the /auth/callback endpoint processes tokens correctly."""
    # Mock the token response from Keycloak
    mock_token = {
        "access_token": "mock-access-token",
        "id_token": create_mock_id_token({
            "sub": "test-user-id",
            "preferred_username": "testuser",
            "email": "test@example.com",
            "exp": 9999999999,  # Far future
            "iat": 1600000000,
            "iss": "https://keycloak.example.com/auth/realms/test-realm",
            "aud": "test-client"
        })
    }
    
    mock_keycloak.authorize_access_token = MagicMock()
    mock_keycloak.authorize_access_token.return_value = mock_token
    
    # Mock JWT decode and validate
    mock_claims = MagicMock()
    mock_claims.validate.return_value = True
    mock_jwt_decode.return_value = mock_claims
    
    # Call the callback endpoint
    with patch("fluvius.fastapi.auth.decode_id_token", return_value={"sub": "test-user-id"}):
        response = auth_client.get("/auth/callback", allow_redirects=False)
        assert response.status_code in (302, 307)  # Redirect status codes
        assert "id_token" in response.cookies


def test_logout_endpoint(auth_client):
    """Test the logout endpoint clears session."""
    response = auth_client.get("/auth/logout")
    assert response.status_code == 200
    assert "Logged out" in response.json()["message"]
