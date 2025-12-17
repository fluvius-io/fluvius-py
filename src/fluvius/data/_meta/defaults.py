DEBUG = False

DATA_ID_TYPE = "UUID4"  # ULID, UUID1, UUID4, OBJECTID
DEFAULT_DATASTORE = 'memory'
DEFAULT_DOMAIN_IDENTIFIER_FIELD = "_iid"
DEFAULT_DOMAIN_SCOPING_FIELD = "_did"
DEFAULT_RECORD_INVALIDATE_FIELD = "_deleted"
IGNORE_COMMAND_EXTRA_FIELDS = True
UUID5_NAMESPACE = 'f853f38d-83f8-4ef4-9e1b-12b9e27bc1ad'

SQLALCHEMY_DIALECT = 'sqlite'  # sqlite | postgresql
BACKEND_QUERY_DEFAULT_LIMIT = 100
BACKEND_QUERY_INTERNAL_LIMIT = 1000

DB_DSN = "sqlite+aiosqlite:////tmp/fluvius_data.sqlite"

# This only works with postgres, for sqlite set DB_CONFIG = {}
DB_CONFIG = dict(
    isolation_level='READ COMMITTED',
    pool_recycle=1800,
    pool_size=10,
    pool_timeout=10,
    max_overflow=20
)
