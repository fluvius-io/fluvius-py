DB_DSN = None
DEBUG_EXCEPTION = False
DEBUG_INGRESS = True
DEFAULT_ACCEPT_HEADER = "json/array"
IGNORE_COMMAND_EXTRA_FIELDS = True

# https://tools.ietf.org/id/draft-idempotency-header-01.html
IDEMPOTENCY_KEY = 'Idempotency-Key'
RESPONSE_STATUS_KEY = 'Response-Status'
CQRS_SOURCE = None
ENABLE_PROFILER = True


# Keycloak configuration
KC_CLIENT_ID = "sanic-app"
KC_CLIENT_SECRET = "your-client-secret"
KC_REALM = "master"
KC_SERVER_URL = "http://localhost:8080"
KC_ACCESS_TOKEN_EXPIRATION = 86400  # 24 hours in seconds
KC_CLIENT_PRIVATE_KEY = None
KC_CLIENT_PRIVATE_KEY_FILE = None
