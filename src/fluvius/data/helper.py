import inspect
import secrets
import datetime

from fluvius.data.identifier import identifier_factory  # noqa


NONE_TYPE = type(None)


def nullable(*types):
    return (NONE_TYPE, *types)


def generate_etag(ctx=None, **kwargs):
    return secrets.token_urlsafe()


def timestamp():
    return datetime.datetime.now(datetime.UTC)




