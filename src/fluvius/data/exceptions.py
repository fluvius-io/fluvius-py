from fluvius.error import (  # noqa
    NotFoundError,
    BadRequestError,
    UnprocessableError
)


class StateCommittedError(UnprocessableError):
    pass


class ItemNotFoundError(NotFoundError):
    pass


class NoItemModifiedError(NotFoundError):
    pass


class MultipleResultsError(UnprocessableError):
    pass


# =============================================================================
# Database-specific exceptions for SQLAlchemy driver
# =============================================================================

class DatabaseError(UnprocessableError):
    """Base class for all database-related errors"""
    label = "Database Error"
    errcode = "DB00.000"


class DuplicateEntryError(DatabaseError):
    """Raised when a unique constraint is violated"""
    label = "Duplicate Entry"
    errcode = "DB00.001"


class IntegrityConstraintError(DatabaseError):
    """Raised when an integrity constraint (foreign key, check, etc.) is violated"""
    label = "Integrity Constraint Violation"
    errcode = "DB00.002"


class DatabaseConnectionError(DatabaseError):
    """Raised when the database is unreachable or connection fails"""
    label = "Database Connection Error"
    errcode = "DB00.003"


class QuerySyntaxError(DatabaseError):
    """Raised when there is a syntax or structure error in the query"""
    label = "Query Syntax Error"
    errcode = "DB00.004"


class DatabaseAPIError(DatabaseError):
    """Raised for general DBAPI errors"""
    label = "Database API Error"
    errcode = "DB00.005"


class UnexpectedDatabaseError(DatabaseError):
    """Raised for unexpected/unknown database errors"""
    label = "Unexpected Database Error"
    errcode = "DB00.007"


class InvalidQueryValueError(BadRequestError):
    """Raised when query contains invalid values (e.g., undefined function, invalid offset)"""
    label = "Invalid Query Value"
    errcode = "DB00.040"


class DatabaseConfigurationError(BadRequestError):
    """Raised when database configuration is invalid or missing"""
    label = "Database Configuration Error"
    errcode = "DB00.100"


class DatabaseTransactionError(UnprocessableError):
    """Raised for transaction-related errors (nested transactions, missing transaction context)"""
    label = "Database Transaction Error"
    errcode = "DB00.106"


class DataSchemaError(BadRequestError):
    """Raised when data schema is invalid or not registered"""
    label = "Data Schema Error"
    errcode = "DB00.105"
