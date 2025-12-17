from contextlib import asynccontextmanager
from datetime import datetime
from dataclasses import is_dataclass, dataclass, field
from fluvius.helper import camel_to_lower, validate_lower_dash
from fluvius.data import logger, config
from fluvius.data.constant import *
from fluvius.data.exceptions import DataSchemaError

_DEBUG = config.DEBUG
_DRIVER_REGISTRY = {}


class DataDriver(object):
    __data_schema_base__ = None

    def __init_subclass__(cls):
        key = cls.__name__
        if key in _DRIVER_REGISTRY:
            raise ValueError(f'Data storage driver already registered: {key}')

        cls.__data_schema_registry__ = {}
        _DRIVER_REGISTRY[key] = cls
        _DEBUG and logger.info('Registered data driver: %s => %s', key, cls)

    def connect(self, **kwargs):
        raise NotImplementedError('DataDriver.connect is not implemented.')
    
    @classmethod
    def lookup_data_schema(cls, schema):
        try:
            if isinstance(schema, str):
                return cls.__data_schema_registry__[schema]

            if cls.__data_schema_base__ and issubclass(schema, cls.__data_schema_base__):
                return schema

            raise DataSchemaError(f'Invalid resource specification: {schema}')
        except KeyError:
            raise DataSchemaError(f'Data schema is not registered: {schema}')

    @classmethod
    def register_schema(cls, data_schema=None, /, name=None):
        def gen_table_name(data_schema, custom_name):
            if custom_name is not None:
                return validate_lower_dash(custom_name)

            if not hasattr(data_schema, '__tablename__'):
                data_schema.__tablename__ = camel_to_lower(data_schema.__name__)

            return data_schema.__tablename__

        def _decorator(schema_cls):
            schema_name = gen_table_name(data_schema, name)
            if schema_name in cls.__data_schema_registry__:
                raise DataSchemaError(f'Schema model already registered: {schema_name}')

            schema = cls.validate_data_schema(schema_cls)
            if hasattr(schema, '__data_schema__'):
                raise DataSchemaError(f'Model already registered else where [{schema}]')

            if cls.__data_schema_base__ and not issubclass(schema, cls.__data_schema_base__):
                raise DataSchemaError(f'Invalid data schema [{schema_cls}] for data driver [{cls}]. Must be subclass of {cls.__data_schema_base__}')

            schema.__data_schema__ = schema_name
            cls.__data_schema_registry__[schema_name] = schema
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

