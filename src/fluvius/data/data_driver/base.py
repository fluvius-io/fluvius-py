from contextlib import asynccontextmanager
from datetime import datetime
from dataclasses import is_dataclass, dataclass, field
from fluvius.helper import camel_to_lower
from fluvius.data import logger, config
from fluvius.data.constant import *

_DEBUG = config.DEBUG
_DRIVER_REGISTRY = {}


class UnregisteredDataSchemaError(RuntimeError):
    pass


class DataDriver(object):
    def __init_subclass__(cls):
        key = cls.__name__
        if key in _DRIVER_REGISTRY:
            raise ValueError(f'Data storage driver already registered: {key}')

        cls._schema_model = {}
        _DRIVER_REGISTRY[key] = cls
        _DEBUG and logger.info('Registered data driver: %s => %s', key, cls)

    def connect(self, **kwargs):
        raise NotImplementedError('DataDriver.connect is not implemented.')
    
    @classmethod
    def lookup_data_schema(cls, resource):
        try:
            return cls._schema_model[resource]
        except KeyError:
            raise UnregisteredDataSchemaError(f'Data schema is not registered: {resource}')

    @classmethod
    def register_schema(cls, resource):
        def _decorator(schema_model):
            if resource in cls._schema_model:
                raise ValueError(f'Schema model already registered: {resource}')

            cls._schema_model[resource] = cls.validate_schema_model(schema_model)
            return schema_model

        return _decorator

    @classmethod
    def validate_schema_model(cls, schema_model):
        return schema_model

    @asynccontextmanager
    async def transaction(self, *args, **kwargs):
        raise NotImplementedError('DataDriver.transaction is not implemented.')

    async def flush(self):
        raise NotImplementedError('DataDriver.flush is not implemented.')

