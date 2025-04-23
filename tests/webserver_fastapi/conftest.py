import pytest
from unittest.mock import patch, MagicMock
from typing import Dict, Any, Generator


@pytest.fixture
def mock_keycloak_config():
    """Provide mock Keycloak configuration for tests."""
    config = {
        "KEYCLOAK_BASE_URL": "https://keycloak.example.com/auth",
        "KEYCLOAK_REALM": "test-realm",
        "KEYCLOAK_CLIENT_ID": "test-client",
        "KEYCLOAK_CLIENT_SECRET": "test-secret",
        "DEFAULT_REDIRECT_URI": "http://localhost:8000/auth/callback",
        "APPLICATION_SECRET_KEY": "test-secret-key",
        "SESSION_COOKIE": "session",
        "COOKIE_HTTPS_ONLY": False,
        "COOKIE_SAME_SITE_POLICY": "lax",
        "APPLICATION_NAME": "Test Application",
        "APPLICATION_SERIAL_NUMBER": "1.0.0",
        "APPLICATION_BUILD_TIME": "2025-04-21T12:00:00Z"
    }
    
    with patch("fluvius.fastapi.config", **config):
        yield config


@pytest.fixture
def mock_jwks_keyset() -> Dict[str, Any]:
    """Mock the JWKS keyset for JWT verification."""
    mock_jwks = {
        "keys": [
            {
                "kid": "test-key-id",
                "kty": "RSA",
                "alg": "RS256",
                "use": "sig",
                "n": "test-modulus",
                "e": "AQAB"
            }
        ]
    }
    return mock_jwks


@pytest.fixture
def mock_domain_context() -> Generator[MagicMock, None, None]:
    """Mock domain context for FastAPI tests."""
    mock_context = MagicMock()
    mock_context.serialize.return_value = {
        "domain": "generic-object",
        "user_id": "test-user-id",
        "tenant_id": "test-tenant-id"
    }
    
    yield mock_context
