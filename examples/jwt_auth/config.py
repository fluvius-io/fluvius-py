import os

# Keycloak settings
KEYCLOAK_SERVER_URL = os.environ.get("KEYCLOAK_SERVER_URL", "http://localhost:8080")
KEYCLOAK_REALM = os.environ.get("KEYCLOAK_REALM", "master")
KEYCLOAK_CLIENT_ID = os.environ.get("KEYCLOAK_CLIENT_ID", "jwt-auth-example")
KEYCLOAK_CLIENT_SECRET = os.environ.get("KEYCLOAK_CLIENT_SECRET", "")

# Application settings
PORT = int(os.environ.get("PORT", 8000))
HOST = os.environ.get("HOST", "0.0.0.0")
DEBUG = os.environ.get("DEBUG", "True").lower() in ("true", "1", "yes")
SECRET_KEY = os.environ.get("SECRET_KEY", "your-secret-key-change-this-in-production")

# JWT settings
JWT_ALGORITHM = "RS256"
JWT_HEADER_PREFIX = "Bearer"

# OAuth2 settings
AUTH_REDIRECT_URI = os.environ.get("AUTH_REDIRECT_URI", "http://localhost:8000/auth/callback")

# JWKS cache settings
JWKS_CACHE_TTL = 3600  # 1 hour