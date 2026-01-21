import os
from enum import Enum
from typing import Any
from collections import namedtuple
from pydantic import Field, field_validator
from fluvius.data import DataModel
from fluvius.error import BadRequestError
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
    if v is None:
        return []

    if isinstance(v, str):
        return [v]

    if isinstance(v, (list, tuple)):
        return list(v)

    raise BadRequestError(
        "T00.201",
        f"{v} is not a list",
        None
    )


def _validate_writer(w):
    if w is None:
        return {}

    if isinstance(w, str):
        return {'name': w}

    if not isinstance(w, dict):
        raise BadRequestError(
            "T00.202",
            f"Invalid writer config: {w}",
            None
        )

    return w


class OutputRow(tuple):
    pass


class ReaderConfig(DataModel):
    name: str
    debug_log: str | None = None
    error_log: str | None = None
    transforms: list = Field(default_factory=list)

    @field_validator('transforms', mode='before')
    @classmethod
    def validate_transforms(cls, v):
        return _validate_list(v)


class WriterConfig(DataModel):
    name: str
    transforms: list = Field(default_factory=list)

    @field_validator('transforms', mode='before')
    @classmethod
    def validate_transforms(cls, v):
        return _validate_list(v)


class PipelineConfig(DataModel):
    key: str
    transaction: str | None = None
    mapping: dict
    transforms: list = Field(default_factory=list)
    writer: dict = Field(default_factory=dict)
    coercer_profile: str = 'generic'
    allow_ctx_buffer: bool = True

    @field_validator('transforms', mode='before')
    @classmethod
    def validate_transforms(cls, v):
        return _validate_list(v)

    @field_validator('writer', mode='before')
    @classmethod
    def validate_writer(cls, v):
        return _validate_writer(v)


class DataProcessManagerConfig(DataModel):
    name: str
    process_name: str
    process_tracker: dict
    force_import: bool = False


class DataProcessConfig(DataModel):
    inputs: dict = Field(default_factory=dict)
    manager: DataProcessManagerConfig | None = None
    reader: dict = Field(default_factory=dict)
    writer: dict = Field(default_factory=dict)
    pipelines: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)

    @field_validator('inputs', mode='before')
    @classmethod
    def validate_inputs(cls, v):
        return _validate_writer(v)

    @field_validator('writer', mode='before')
    @classmethod
    def validate_writer_field(cls, v):
        return _validate_writer(v)

    @field_validator('manager', mode='before')
    @classmethod
    def validate_manager(cls, v):
        if v is None:
            return None
        if isinstance(v, DataProcessManagerConfig):
            return v
        if isinstance(v, dict):
            return DataProcessManagerConfig(**v)
        return v


class InputFile(DataModel):
    filename: str
    filepath: str
    filesize: Any = None
    filetype: Any = None
    source_id: int | None = None
    sha256sum: str | None = None
    metadata: Any = None

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
