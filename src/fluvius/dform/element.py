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

import hashlib
import json
import uuid
from typing import Optional, Dict, Any, ClassVar, Type, get_origin, get_args

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg
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
    FormConnector  # noqa: F401
)


DFORM_DATA_SCHEMA = config.DFORM_DATA_SCHEMA
DFORM_DEFS_SCHEMA = config.DFORM_DEFS_SCHEMA
DB_DSN = config.DB_DSN



class ElementDataManager(DataAccessManager):
    """Data manager for element data storage in DB_SCHEMA_ELEMENT"""
    __connector__ = FormConnector
    __automodel__ = True


class ElementSchema(FormConnector.pgschema(), DomainSchema):
    __abstract__ = True


model_mapper = PydanticSQLAlchemyMapper(ElementSchema, schema=DFORM_DATA_SCHEMA)


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
    title: str
    description: Optional[str] = None
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


class DataElementModel(DataModel):
    """
    Base class for element data schema registration.
    
    This class is used for registering element types via Meta classes.
    Element data is stored in FormElement (defined in schema.py).
    
    Element types are registered by creating subclasses with Meta classes:
    
    Example:
        class TextInputData(DataModel):
            value: str
        
        class TextInputElementModel(ElementModel):
            class Meta:
                key = "text-input"
                name = "Text Input"
                desc = "A text input element"
    
    Note: FormElement (in schema.py) is used for actual data storage.
    ElementModel is only for registration purposes.
    """

    class Meta:
        pass

    class DataProvider(ElementDataProvider):
        pass

    @classmethod
    def _type_to_string(cls, annotation: Any) -> str:
        """Convert a type annotation to a stable string representation."""
        if annotation is None:
            return "None"
        
        # Handle basic types
        if isinstance(annotation, type):
            return f"{annotation.__module__}.{annotation.__qualname__}"
        
        # Handle generic types (List[str], Optional[int], etc.)
        origin = get_origin(annotation)
        if origin is not None:
            args = get_args(annotation)
            origin_str = cls._type_to_string(origin)
            args_str = ", ".join(cls._type_to_string(arg) for arg in args)
            return f"{origin_str}[{args_str}]"
        
        # Fallback to string representation
        return str(annotation)

    @classmethod
    def element_signature(cls) -> str:
        """
        Generate a stable hash/UUID that is unique to the model's field structure.
        
        The signature is based on:
        - Field names
        - Field types (annotations)
        - Field defaults
        - Field metadata (constraints, validators, etc.)
        
        Returns:
            A UUID string that uniquely identifies this model's schema structure.
        """
        fields_info = []
        
        for field_name, field_info in sorted(cls.model_fields.items()):
            field_data = {
                "name": field_name,
                "type": cls._type_to_string(field_info.annotation),
                "is_required": field_info.is_required(),
            }
            
            # Include default value if present (use repr for stable serialization)
            if field_info.default is not None:
                field_data["default"] = repr(field_info.default)
            
            if field_info.default_factory is not None:
                # Use the factory's qualified name for stability
                factory = field_info.default_factory
                if hasattr(factory, '__qualname__'):
                    field_data["default_factory"] = factory.__qualname__
                else:
                    field_data["default_factory"] = str(factory)
            
            # Include field constraints/metadata if present
            if field_info.title:
                field_data["title"] = field_info.title
            if field_info.description:
                field_data["description"] = field_info.description
            if field_info.alias:
                field_data["alias"] = field_info.alias
            
            fields_info.append(field_data)
        
        # Create a deterministic JSON string
        canonical_str = json.dumps(fields_info, sort_keys=True, separators=(',', ':'))
        
        # Generate SHA-256 hash
        hash_bytes = hashlib.sha256(canonical_str.encode('utf-8')).digest()
        
        # Convert to UUID5-style UUID using the hash (first 16 bytes)
        # This creates a deterministic UUID from the hash
        return str(uuid.UUID(bytes=hash_bytes[:16], version=5))


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
            'title': getattr(meta_cls, 'title', cls.__name__),
            'description': getattr(meta_cls, 'description', cls.__doc__),
            'table_name': getattr(meta_cls, 'table_name', camel_to_lower(cls.__name__)),
        })

        # Auto-generate Schema from Model if not provided
        # Requires __tablename__ to be set on the subclass
        if cls.Schema is None:
            # Ensure model fields are populated (Pydantic v2)
            if not cls.model_fields:
                try:
                    cls.model_rebuild(force=True)
                except Exception:
                    # Ignore if rebuild fails (might be abstract or partial)
                    pass

            # Fallback: if model_fields empty (e.g. during initialization), inspect annotations manually
            # This happens if Pydantic hasn't fully populated the class yet
            extra_columns = {}
            if not cls.model_fields and hasattr(cls, '__annotations__'):
                from pydantic.fields import FieldInfo
                for name, annotation in cls.__annotations__.items():
                    if name.startswith('_'): continue
                    
                    # Create column manually
                    try:
                        col = model_mapper.create_column(name, annotation, FieldInfo(annotation=annotation))
                        extra_columns[name] = col
                    except Exception:
                        pass
            
            # Create schema class with any extra columns found via fallback
            cls.Schema = model_mapper.create_table_class(
                cls, 
                cls.Meta.table_name, 
                extra_columns=extra_columns if extra_columns else None
            )
        
        # Validate required fields
        if not cls.Meta.key:
            raise InternalServerError(
                "F00.103",
                f"ElementModel subclass {cls.__name__} Meta must define key",
                None
            )
        
        if not cls.Meta.title:
            raise InternalServerError(
                "F00.104",
                f"ElementModel subclass {cls.__name__} Meta must define title",
                None
            )
        
        # Validate Schema if provided
        if cls.Schema is not None and not issubclass(cls.Schema, ElementSchema):
            raise InternalServerError('F00.201', f'Invalid element schema: {cls.Schema}')

        if not issubclass(cls.DataProvider, ElementDataProvider):
            raise InternalServerError('F00.203', f'Invalid element data provider: {cls.DataProvider}')

        # Automatically register the schema in the registry using key
        # Use register() method with the key
        ElementModelRegistry.register(cls.Meta.key)(cls)


# Registry for ElementModel subclasses
# Registration happens automatically via __init_subclass__
ElementModelRegistry = ClassRegistry(DataElementModel)
