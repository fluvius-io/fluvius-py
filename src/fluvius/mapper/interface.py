import os
from enum import Enum
from pyrsistent import PClass, field
from collections import namedtuple


# key: str, value: scalar, context: str, depth: int
DataElement = namedtuple("DataElement", "key value meta", defaults=(None, None, None))
DataLoop = namedtuple("DataLoop", "id elements depth meta", defaults=(None, None, None))

# index, object: dict of key, value of input, context: list of context element
DataObject = namedtuple("DataObject", "index object context")


class InputResourceKind(Enum):
    FILE = 'FILE'
    S3FILE = 'S3FILE'
    REST_API = 'REST_API'


def _validate_list(v):
    if isinstance(v, str):
        return [v]

    if isinstance(v, (list, tuple)):
        return v

    raise ValueError('%s is not a list' % v)


def _validate_writer(w):
    if isinstance(w, str):
        return {'name': w}

    if not isinstance(w, dict):
        raise ValueError('Invalid writer config: %s', w)

    return w


class OutputRow(tuple):
    pass


class ReaderConfig(PClass):
    name             = field(type=str)
    debug_log        = field(type=(str, type(None)), initial=lambda: None)
    error_log        = field(type=(str, type(None)), initial=lambda: None)
    transforms       = field(type=list, initial=list, factory=_validate_list)


class WriterConfig(PClass):
    name             = field(type=str)
    transforms       = field(type=list, initial=list, factory=_validate_list)


class PipelineConfig(PClass):
    key              = field(type=str)
    transaction      = field(type=(str, type(None)), initial=lambda: None)
    mapping          = field(type=dict)
    transforms       = field(type=list, initial=list, factory=_validate_list)
    writer           = field(type=dict, initial=dict, factory=_validate_writer)
    coercer_profile  = field(type=str, initial=lambda: 'generic')


class DataProcessManagerConfig(PClass):
    process_name    = field(type=str)
    force_import    = field(type=bool, initial=lambda: False)


class DataProcessConfig(PClass):
    inputs          = field(type=dict, initial=dict, factory=_validate_writer)
    manager         = field(type=(DataProcessManagerConfig, type(None)))
    reader          = field(type=dict, initial=dict)
    writer          = field(type=dict, initial=dict, factory=_validate_writer)
    pipelines       = field(type=dict, initial=dict)
    metadata        = field(type=dict, initial=dict)


class InputFile(PClass):
    filename = field(type=str)
    filepath = field(type=str)
    source_id = field(type=(int, type(None)), initial=lambda: None)
    sha256sum = field(type=(str, type(None)), initial=lambda: None)

    @classmethod
    def from_file(cls, filepath, **kwargs):
        name = os.path.basename(filepath)
        path = os.path.abspath(filepath)
        return cls(filename=name, filepath=path, **kwargs)


ReaderFinished = type("ReaderFinished")()


class InputAlreadyProcessedError(Exception):
    pass


class ReaderError(Exception):
    pass


class ResourceMeta(dict):
    pass
