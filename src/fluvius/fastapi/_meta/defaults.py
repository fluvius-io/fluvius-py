from fluvius import __version__
from fluvius.helper.timeutil import timestamp

APPLICATION_BUILD_TIME = str(timestamp())
APPLICATION_DESC = 'Fluvius API Application (Update config to change this)'
APPLICATION_NAME = 'Fluvius API'
APPLICATION_SECRET_KEY = "super-secret-session-key-IUUUCBhv4NRDVB4ONpe8lcNJJY"
APPLICATION_ROOT = "/api"
APPLICATION_SERIAL_NUMBER = 1001
APPLICATION_VERSION = __version__
AUTH_PROFILE_PROVIDER = None
COOKIE_HTTPS_ONLY = False       # Set True in production
COOKIE_SAME_SITE_POLICY = "strict" # or "strict" for tighter CSRF
DEFAULT_CALLBACK_URI = "http://localhost:8000/auth/callback"
DEFAULT_LOGOUT_REDIRECT_URI = "/auth/verify"
DEFAULT_SIGNIN_REDIRECT_URI = "/auth/info"
DEVELOPER_MODE = True
KEYCLOAK_BASE_URL = "https://id.adaptive-bits.com/auth"
KEYCLOAK_CLIENT_ID = "sample_app"
KEYCLOAK_CLIENT_SECRET = "W2kAi1iqvVJhrAMVj1YnVQXx0GxNUDiV"  # Omit for public clients
KEYCLOAK_REALM = "dev-1.fluvius.io"
SESSION_COOKIE = "session"
SAFE_REDIRECT_DOMAINS = ["localhost",]
RESP_HEADER_IDEMPOTENCY = 'Idempotency-Key'
RESP_HEADER_RESPONSE_STATUS = 'Response-Status'

WHITELIST_DOMAIN = None
BLACKLIST_DOMAIN = None
