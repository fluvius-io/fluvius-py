APPLICATION_SECRET_KEY = "super-secret-session-key-IUUUCBhv4NRDVB4ONpe8lcNJJY"
COOKIE_HTTPS_ONLY = False       # Set True in production
COOKIE_SAME_SITE_POLICY = "strict" # or "strict" for tighter CSRF
KEYCLOAK_BASE_URL = "https://id.adaptive-bits.com/auth"
KEYCLOAK_CLIENT_ID = "sample_app"
KEYCLOAK_CLIENT_SECRET = "W2kAi1iqvVJhrAMVj1YnVQXx0GxNUDiV"  # Omit for public clients
KEYCLOAK_REALM = "dev-1.fluvius.io"
DEFAULT_REDIRECT_URI = "http://localhost:8000/auth/callback"
SESSION_COOKIE = "session"

