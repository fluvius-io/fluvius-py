import re
import enum
from fluvius.data.helper import identifier_factory, nullable, generate_etag, when, timestamp  # noqa -- @TODO: remove after resolve compatibility
from fluvius.error import BadRequestError

RX_CQRS_IDENTIFIER = re.compile(
    r"^([a-z][a-z\d\-]*[a-z\d]\.)*([a-z][a-z\d\-]*[a-z\d])$"
)

CQRS_AUTO_FIELDS = (
    "_updated",
    "_created",
    "_deleted",
    "_etag",
    "_creator",
    "_updater"
)

class _AGGROOT_RESOURCES(enum.Enum):
    ALL = 'ALL'
    ANY = ALL
    N_A = 'N_A'


def consume_queue(q):
    while not q.empty():
        yield q.get()
        q.task_done()


def validate_identifier(key):
    if not RX_CQRS_IDENTIFIER.match(key):
        raise ValueError(f"Invalid CQRS identifier: {key}")

    return key


def cleanup_auto_fields(data: dict, extra_fields=None):
    cleanup_fields = CQRS_AUTO_FIELDS if extra_fields is None \
        else CQRS_AUTO_FIELDS + tuple(extra_fields)

    def _process_value(val):
        if isinstance(val, dict):
            return dict(_process(val))

        if isinstance(val, (list, tuple)):
            return [_process_value(v) for v in val]

        return val

    def _process(data):
        for k, v in data.items():
            if k in cleanup_fields:
                continue

            yield k, _process_value(v)

    return dict(_process(data))


def prepare_aggroot_spec(resource_spec):
    ''' Prepare the spec for [include_aggroot] '''

    if not resource_spec:
        return _AGGROOT_RESOURCES.N_A

    if isinstance(resource_spec, _AGGROOT_RESOURCES):
        return resource_spec

    if isinstance(resource_spec, str):
        return (resource_spec,)

    if isinstance(resource_spec, tuple):
        return resource_spec

    if isinstance(resource_spec, list):
        return tuple(resource_spec)

    raise ValueError(f'Invalid aggroot resources specification: {resource_spec}')


def include_aggroot(resource, resource_spec):
    ''' Determine if a certain aggroot should be included in an operation
        - True: include the aggroot object
        - False: do not include.
        Otherwise, raise an exception.
    '''

    if resource_spec is _AGGROOT_RESOURCES.N_A:
        return False

    if resource_spec is _AGGROOT_RESOURCES.ALL:
        return True

    if not isinstance(resource_spec, tuple):
        raise ValueError(f'Invalid resource specs: {resource_spec}')

    if resource not in resource_spec:
        raise BadRequestError(f'Unable to operate on resource [{resource}]. Allows: {resource_spec}')

    return True

