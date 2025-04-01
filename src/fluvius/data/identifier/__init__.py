import uuid
import base64
from fluvius.data import config


DEFAULT_UUID5_NAMESPACE = uuid.UUID(config.UUID5_NAMESPACE)


def _gen_uuid5(seed, namespace=DEFAULT_UUID5_NAMESPACE):
    return uuid.uuid5(namespace, seed)


def _gen_base64():
    return base64.urlsafe_b64encode(uuid.uuid4().bytes)


def identifier_factory(value):
    ''' Return an identifier for 3 cases:
        - A fixed value based on a string
        - Original value if it is already and identifier
        - Coerce the current value to a UUID
    '''
    if isinstance(value, UUID_TYPE):
        return value

    try:
        return UUID_TYPE(value)
    except (TypeError, ValueError):
        if value and isinstance(value, str):
            return UUID_GENF(value)

        return None


UUID_TYPE = uuid.UUID  # Identifier class
UUID_GENR = uuid.uuid4  # Generate a random identifier
UUID_GENF = _gen_uuid5  # Generate an identifier deterministicly from a seed within a namespace (optional)
UUID_GENR_BASE64 = _gen_base64  # Generate a random base64 identifier
