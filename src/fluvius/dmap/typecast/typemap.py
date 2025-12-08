from fluvius.error import BadRequestError

DEFAULT_TYPE = 'string'
SUPPORTED_TYPES = (
    'datetime',
    'float',
    'integer',
    'date',
    'text',
    'string',
    'list',
    'map',
    'uuid',
    'bigint',
    'bool'
)


def dtype(_type, default_value=None):
    if _type not in SUPPORTED_TYPES:
        raise BadRequestError(
            "T00.901",
            f"Data type [{_type}] is not supported",
            None
        )

    def decorator(func):
        func.__dtype__ = _type
        func.__dvalue__ = default_value
        return func

    return decorator


def get_dtype(func):
    return getattr(func, '__dtype__', DEFAULT_TYPE)
