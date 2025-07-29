import secrets
from collections.abc import Mapping

from pyrsistent import PClass

from fluvius.data.identifier import identifier_factory  # noqa
from fluvius.helper.timeutil import timestamp
from fluvius.data.data_model import DataModel, BlankModel
from types import SimpleNamespace


NONE_TYPE = type(None)


def nullable(*types):
    return (NONE_TYPE, *types)


def generate_etag(ctx=None, **kwargs):
    return secrets.token_urlsafe()


def serialize_mapping(data):
    if data is None:
        return {}

    if isinstance(data, Mapping):
        return data

    if isinstance(data, DataModel):
        return data.model_dump()

    if isinstance(data, (BlankModel, SimpleNamespace)):
        return data.__dict__

    if isinstance(data, PClass):
        return data.serialize()

    raise ValueError('Unable to convert value to mapping: %s' % str(data.__class__))



