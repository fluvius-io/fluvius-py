import os
from enum import Enum
from pyrsistent import PClass, field
from collections import namedtuple
from fluvius.helper import osutil


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
    name            = field(type=str)
    process_name    = field(type=str)
    process_tracker = field(type=dict)
    force_import    = field(type=bool, initial=lambda: False)


class DataProcessConfig(PClass):
    inputs          = field(type=dict, initial=dict, factory=_validate_writer)
    manager         = field(type=(DataProcessManagerConfig, type(None)), factory=DataProcessManagerConfig.create)
    reader          = field(type=dict, initial=dict)
    writer          = field(type=dict, initial=dict, factory=_validate_writer)
    pipelines       = field(type=dict, initial=dict)
    metadata        = field(type=dict, initial=dict)


class InputFile(PClass):
    filename = field(type=str)
    filepath = field(type=str)
    filesize = field()
    filetype = field()
    source_id = field(type=(int, type(None)), initial=lambda: None)
    sha256sum = field(type=(str, type(None)), initial=lambda: None)
    metadata = field()

    @classmethod
    def from_file(cls, filepath, **kwargs):
        name = os.path.basename(filepath)
        path = os.path.abspath(filepath)
        size = os.path.getsize(filepath)
        csum = osutil.file_checksum_sha256(filepath)
        type = osutil.file_mime(filepath)

        return cls(
            filename=name,
            filepath=path,
            filesize=size,
            filetype=type,
            sha256sum=csum,
            **kwargs
        )


ReaderFinished = type("ReaderFinished")()


class InputAlreadyProcessedError(Exception):
    pass


class ReaderError(Exception):
    pass


class ResourceMeta(dict):
    pass
