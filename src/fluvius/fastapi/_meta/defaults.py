from fluvius import __version__
from fluvius.helper.timeutil import timestamp

APPLICATION_BUILD_TIME = str(timestamp())
APPLICATION_DESC = '[APPLICATION_DESC] Fluvius API Application'
APPLICATION_NAME = '[APPLICATION_NAME] Fluvius API'
APPLICATION_SECRET_KEY = "super-secret-session-key-IUUUCBhv4NRDVB4ONpe8lcNJJY"
APPLICATION_ROOT = "/api"
APPLICATION_SERIAL_NUMBER = 1001
APPLICATION_VERSION = __version__
AUTH_PROFILE_PROVIDER = None

SES_CLIENT_TOKEN_FIELD = "client_token"
SES_ID_TOKEN_FIELD = "id_token"
SES_AC_TOKEN_FIELD = "access_token"
SES_USER_FIELD = "user"
SES_SESSION_ID_FIELD = "session_id"

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

# Redis configuration for MQTT authentication
REDIS_URL = "redis://localhost:6379"

MQTT_CLIENT_CHANNEL = "notify"
MQTT_CLIENT_USER = "system"
MQTT_CLIENT_SECRET = None
MQTT_CLIENT_QOS = 1
MQTT_CLIENT_RETAIN = False
MQTT_BROKER_HOST = None
MQTT_BROKER_PORT = 1883
MQTT_USER_PREFIX = "mqtt"
MQTT_PERMISSIONS = [
    ("last-will", 4),
    ("notify", 4),
    ("contract", 4),
    ("base", 4),
    ("work", 4),
]

MQTT_DEBUG = True
VALIDATE_CSRF_TOKEN = False
AUTH_REALMS_CONFIG = {}
ERROR_TRACKING_PROVIDER = "NullTracker" # "PosthogTracker" or "SentryTracker"
