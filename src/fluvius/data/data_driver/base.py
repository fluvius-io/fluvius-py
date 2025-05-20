from contextlib import asynccontextmanager
from datetime import datetime
from dataclasses import is_dataclass, dataclass, field
from fluvius.helper import camel_to_lower, validate_lower_dash
from fluvius.data import logger, config, DataModel
from fluvius.data.constant import *

_DEBUG = config.DEBUG
_DRIVER_REGISTRY = {}


class DataSchemaError(ValueError):
    pass


class DataDriver(object):
    __schema_baseclass__ = DataModel

    def __init_subclass__(cls):
        key = cls.__name__
        if key in _DRIVER_REGISTRY:
            raise ValueError(f'Data storage driver already registered: {key}')

        cls._data_schema = {}
        _DRIVER_REGISTRY[key] = cls
        _DEBUG and logger.info('Registered data driver: %s => %s', key, cls)

    def connect(self, **kwargs):
        raise NotImplementedError('DataDriver.connect is not implemented.')
    
    @classmethod
    def lookup_data_schema(cls, resource):
        try:
            if isinstance(resource, str):
                return cls._data_schema[resource]

            if issubclass(resource, cls.__schema_baseclass__):
                return resource

            raise DataSchemaError(f'Invalid resource specification: {resource}')
        except KeyError:
            raise DataSchemaError(f'Data schema is not registered: {resource}')

    @classmethod
    def register_schema(cls, data_schema=None, /, name=None):
        def gen_schema_name(data_schema, custom_name):
            if custom_name is not None:
                return validate_lower_dash(custom_name)

            name = camel_to_lower(data_schema.__name__)

            if not hasattr(data_schema, '__tablename__'):
                data_schema.__tablename__ = name

            return name

        def _decorator(schema_cls):
            schema_name = gen_schema_name(schema_model, name)
            if schema_name in cls._data_schema:
                raise DataSchemaError(f'Schema model already registered: {schema_name}')

            schema = cls.validate_data_schema(schema_cls)
            if hasattr(schema, '__data_schema__'):
                raise DataSchemaError(f'Model already registered else where [{schema}]')

            if not issubclass(schema, cls.__schema_baseclass__):
                raise DataSchemaError(f'Invalid data schema [{schema_cls}] for data driver [{cls}]')

            schema.__data_schema__ = schema_name
            cls._data_schema[schema_name] = schema
            return schema_cls

        if data_schema is None:
            return _decorator

        return _decorator(data_schema)

    @classmethod
    def validate_data_schema(cls, schema_model):
        return schema_model

    @asynccontextmanager
    async def transaction(self, *args, **kwargs):
        raise NotImplementedError('DataDriver.transaction is not implemented.')

    async def flush(self):
        raise NotImplementedError('DataDriver.flush is not implemented.')

