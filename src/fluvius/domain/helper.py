import re
import enum

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



