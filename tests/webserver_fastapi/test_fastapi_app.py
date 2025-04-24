import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Import the app to test
from fastapi_app.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_auth_context():
    """Mock the auth context for protected endpoints."""
    test_user = {
        "sub": "test-user-id",
        "preferred_username": "testuser",
        "email": "test@example.com",
        "name": "Test User",
        "roles": ["user"]
    }
    
    auth_context = MagicMock()
    auth_context.user = test_user
    return auth_context


def test_root_endpoint(client):
    """Test the root endpoint returns the expected Swagger UI."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "swagger" in response.text.lower()


def test_protected_endpoint_unauthorized(client):
    """Test that the protected endpoint returns 401 without auth."""
    response = client.get("/protected")
    assert response.status_code == 401
    assert "Not authenticated" in response.text


@patch("fastapi.Request.state")
def test_protected_endpoint_authorized(mock_state, client, mock_auth_context):
    """Test the protected endpoint with a mocked authenticated user."""
    # Configure the state mock to have auth attribute
    mock_state.auth = mock_auth_context
    
    # Add headers that would normally be set by auth middleware
    response = client.get(
        "/protected", 
        headers={"Authorization": "Bearer mock-token"}
    )
    
    # If our patching worked correctly
    assert response.status_code == 200
    assert "Hello testuser" in response.json()["message"]
    assert response.json()["user"]["preferred_username"] == "testuser"


def test_app_summary_endpoint(client):
    """Test the app summary endpoint returns application info."""
    response = client.get("/~metadata")
    assert response.status_code == 200
    assert "name" in response.json()
    assert "serial_no" in response.json()
    assert "build_time" in response.json()


def test_domain_registration():
    """Test that the ObjectDomain is properly registered."""
    from fluvius.fastapi.domain import FastAPIDomainManager
    from object_domain.domain import ObjectDomain
    
    # Check if ObjectDomain is in the registered domains
    assert ObjectDomain.__domain__ in FastAPIDomainManager.get_domains()
    
    # Verify the domain is configured correctly
    domain_instance = FastAPIDomainManager.get_domain(ObjectDomain.__domain__)
    assert domain_instance is not None
    assert domain_instance.__domain__ == "generic-object"
