import secrets
from collections.abc import Mapping

from pyrsistent import PClass
from sqlalchemy.orm import DeclarativeMeta

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

    # Check if the class is a SQLAlchemy Declarative Model
    if isinstance(data.__class__, DeclarativeMeta):
        return data.serialize()

    raise ValueError(f'Unable to convert value to mapping [{data.__class__}]')


def parse_table_args(table_args):
    args = []
    opts = {}

    if not table_args:
        return args, opts

    if isinstance(table_args, dict):
        opts.update(table_args)
    else:
        for entry in table_args:
            if isinstance(entry, dict):
                opts.update(entry)
            else:
                args.append(entry)

    return args, opts

def merge_table_args(base_cls, child_cls):
    base_args = getattr(base_cls, '__table_args__', None)
    child_args = getattr(child_cls, '__table_args__', None)

    if not child_args:
        return base_args

    if not base_args:
        return child_args

    args, opts = parse_table_args(base_args)
    child_args, child_opts = parse_table_args(child_args)

    args.extend(child_args)
    opts.update(child_opts)
    return tuple(args + [opts]) if opts else tuple(args)
