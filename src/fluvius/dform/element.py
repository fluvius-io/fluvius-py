"""
Element Type System

Element types are created by inheriting ElementModel schema with a new table name
and updated structure. Each element data schema defines a new element type and
optionally has a Meta object containing the element type key, title, desc,
data schema (optional), etc.

Usage:
    class TextInputElementModel(ElementModel):
        value: str

        class Meta:
            key = "text-input"
            name = "Text Input"
            desc = "A text input element"
            table_name = "text_input_element_data"
        
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg
from typing import Optional, Dict, Any, ClassVar, Type
from pydantic import Field

from fluvius.data import DataModel, DomainSchema, FluviusJSONField
from fluvius.helper import ClassRegistry, ImmutableNamespace, camel_to_lower
from fluvius.data import DataAccessManager
from fluvius.error import BadRequestError, InternalServerError

"""
Element Data Storage Schema

This module defines the schema for storing element data in DB_SCHEMA_ELEMENT.
Element data is validated by element type classes before being saved.
"""
from . import config
from .mapper import PydanticSQLAlchemyMapper


# Import form schema tables to ensure they're registered in metadata
# This is necessary for cross-schema foreign key references
# Even with use_alter=True, SQLAlchemy needs to know about the referenced tables
from .schema import (
    FormConnector, DocumentForm, ElementInstance, ElementDefinition,
    ElementGroupInstance, FormDefinition, DocumentSection  # noqa: F401
)


DFORM_DATA_DB_SCHEMA = config.DFORM_DATA_DB_SCHEMA
DEFINITION_DB_SCHEMA = config.DEFINITION_DB_SCHEMA
DB_DSN = config.DB_DSN



class ElementDataManager(DataAccessManager):
    """Data manager for element data storage in DB_SCHEMA_ELEMENT"""
    __connector__ = FormConnector
    __automodel__ = True


class ElementSchema(FormConnector.pgschema(), DomainSchema):
    __abstract__ = True


model_mapper = PydanticSQLAlchemyMapper(ElementSchema, schema=DFORM_DATA_DB_SCHEMA)


class ElementMeta(DataModel):
    """
    Metadata for ElementModel schemas.
    
    Each ElementModel subclass can define a Meta class with:
    - key: Unique identifier for the element type (required)
    - name: Human-readable name (required)
    - desc: Description (optional)
    - element_schema: DataModel class for validation (optional)
    - attrs: Additional configuration (optional)
    """
    key: str
    name: str
    desc: Optional[str] = None
    table_name: Optional[str] = None



class ElementDataProvider(object):
    __config__ = ImmutableNamespace

    def __init__(self, domain, app, **config):
        self._app = app
        self._domain = domain
        self._config = self.validate_config(config)

    def validate_config(self, config, **defaults):
        config = defaults | config
        return self.__config__(**{k.upper(): v for k, v in config.items()})

    @property
    def app(self):
        return self._app

    @property
    def config(self):
        return self._config

    @property
    def domain(self):
        return self._domain

    def populate(self, statemgr, **context):
        return {}


class ElementModel(DataModel):
    """
    Base class for element data schema registration.
    
    This class is used for registering element types via Meta classes.
    Element data is now stored in ElementInstance (defined in schema.py).
    
    Element types are registered by creating subclasses with Meta classes:
    
    Example:
        class TextInputData(DataModel):
            value: str
        
        class TextInputElementModel(ElementModel):
            class Meta:
                key = "text-input"
                name = "Text Input"
                desc = "A text input element"
    
    Note: ElementInstance (in schema.py) is used for actual data storage.
    ElementModel is only for registration purposes.
    """

    class Meta:
        pass

    class Provider(ElementDataProvider):
        pass


    # Note: Schema must be set to None for the base class
    # Subclasses should either:
    # 1. Let the mapper auto-generate Schema from Model (default)
    # 2. Define their own Schema class with __tablename__ and inherit from ElementSchema
    Schema: ClassVar[Optional[Type]] = None
    
    def __init_subclass__(cls, **kwargs):
        """Convert Meta class to ElementMeta instance and register schema"""
        super().__init_subclass__(**kwargs)
        
        if cls.__dict__.get('__abstract__'):
            return
        
        if not hasattr(cls, 'Meta'):
            raise InternalServerError(
                "F00.102",
                f"ElementModel subclass {cls.__name__} must define a Meta class",
                None
            )
        
        # Convert Meta class to ElementMeta instance
        meta_cls = cls.Meta
        cls.Meta = ElementMeta.create(meta_cls, defaults={
            'key': getattr(meta_cls, 'key', None),
            'name': getattr(meta_cls, 'name', cls.__name__),
            'table_name': getattr(meta_cls, 'table_name', camel_to_lower(cls.__name__)),
        })

        # Auto-generate Schema from Model if not provided
        # Requires __tablename__ to be set on the subclass
        if cls.Schema is None:
            cls.Schema = model_mapper.create_table_class(cls, cls.Meta.table_name)
        
        # Validate required fields
        if not cls.Meta.key:
            raise InternalServerError(
                "F00.103",
                f"ElementModel subclass {cls.__name__} Meta must define key",
                None
            )
        
        if not cls.Meta.name:
            raise InternalServerError(
                "F00.104",
                f"ElementModel subclass {cls.__name__} Meta must define name",
                None
            )
        
        # Validate Schema if provided
        if cls.Schema is not None and not issubclass(cls.Schema, ElementSchema):
            raise InternalServerError('F00.201', f'Invalid element schema: {cls.Schema}')

        if not issubclass(cls.Provider, ElementDataProvider):
            raise InternalServerError('F00.203', f'Invalid element data provider: {cls.Provider}')

        # Automatically register the schema in the registry using key
        # Use register() method with the key
        ElementModelRegistry.register(cls.Meta.key)(cls)


# Registry for ElementModel subclasses
# Registration happens automatically via __init_subclass__
ElementModelRegistry = ClassRegistry(ElementModel)
