from contextlib import asynccontextmanager
from datetime import datetime
from dataclasses import is_dataclass, dataclass, field
from fluvius.helper import camel_to_lower
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
    def register_schema(cls, resource):
        def _decorator(schema_model):
            if resource in cls._data_schema:
                raise DataSchemaError(f'Schema model already registered: {resource}')

            model = cls.validate_data_schema(schema_model)
            if hasattr(model, '__resource_name__'):
                raise DataSchemaError(f'Model already registered else where [{model}]')

            if not issubclass(model, cls.__schema_baseclass__):
                raise DataSchemaError(f'Invalid data schema [{schema_model}] for data driver [{cls}]')

            model.__resource_name__ = resource
            cls._data_schema[resource] = model
            return schema_model

        return _decorator

    @classmethod
    def validate_data_schema(cls, schema_model):
        return schema_model

    @asynccontextmanager
    async def transaction(self, *args, **kwargs):
        raise NotImplementedError('DataDriver.transaction is not implemented.')

    async def flush(self):
        raise NotImplementedError('DataDriver.flush is not implemented.')

