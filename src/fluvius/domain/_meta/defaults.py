DEBUG = False
DB_DSN = ""


CQRS_ID_TYPE = "UUID4"  # ULID, UUID1, UUID4, OBJECTID
IGNORE_COMMAND_EXTRA_FIELDS = False

IF_MATCH_VERIFY = True
IF_MATCH_HEADER = "if-match"
AGGREGATE_VERIFY_ACTION = False

TRACK_MUTATION = False
DEFAULT_RESPONSE_TYPE = 'default-response'
SQL_LOG_STORE_NAMESPACE = 'domain-audit'
SQL_LOG_DB_DSN = "postgresql+asyncpg://fluvius_test:iyHu5WBQxiVXyLLJaYO0XJec@localhost:5432/fluvius_test"
DEVELOPER_MODE = False
