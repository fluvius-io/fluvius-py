"""
Element Type System

Element types are created by inheriting ElementData schema with a new table name
and updated structure. Each element data schema defines a new element type and
optionally has a Meta object containing the element type key, title, desc,
data schema (optional), etc.

Usage:
    class TextInputData(DataModel):
        value: str
    
    class TextInputElementData(ElementData):
        __tablename__ = "text_input_element_data"
        
        class Meta:
            type_key = "text-input"
            type_name = "Text Input"
            desc = "A text input element"
            element_schema = TextInputData  # DataModel class for validation
        
        # Add custom columns as needed
        custom_field = sa.Column(sa.String, nullable=True)
"""
from fluvius.data import DataModel
from fluvius.helper.registry import ClassRegistry
from typing import Optional, Dict, Any, ClassVar, Type
from pydantic import Field
from fluvius.data import DataAccessManager

"""
Element Data Storage Schema

This module defines the schema for storing element data in DB_SCHEMA_ELEMENT.
Element data is validated by element type classes before being saved.
"""
from . import config

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg
from fluvius.data import DomainSchema, FluviusJSONField
from fluvius.error import BadRequestError

# Import form schema tables to ensure they're registered in metadata
# This is necessary for cross-schema foreign key references
# Even with use_alter=True, SQLAlchemy needs to know about the referenced tables
from .schema import FormConnector, DataForm, DataElement  # noqa: F401


DB_SCHEMA_ELEMENT = config.DB_SCHEMA_ELEMENT
DB_SCHEMA_FORM = config.DB_SCHEMA
DB_DSN = config.DB_DSN



class BaseElementType(DataModel):
    """
    Base class for element types.
    
    Each element type subclass must define class attributes:
    - type_key: Unique identifier for the element type
    - type_name: Human-readable name
    - desc: Description (optional)
    - element_schema: DataModel class for validation (optional)
    - attrs: Additional configuration (optional)
    """
    type_key: ClassVar[str]
    type_name: ClassVar[str]
    desc: ClassVar[Optional[str]] = None
    element_schema: ClassVar[Optional[Type[DataModel]]] = None  # DataModel class for validation
    attrs: ClassVar[Optional[Dict[str, Any]]] = None

    @classmethod
    def validate_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate element data against this element type's schema.
        
        Args:
            data: The element data to validate
            
        Returns:
            Validated data dictionary
            
        Raises:
            BadRequestError: If data doesn't match the schema
        """
        if cls.element_schema:
            # Use DataModel validation if element_schema is provided
            try:
                # Instantiate the DataModel class with the data to validate
                validated_instance = cls.element_schema(**data)
                # Convert back to dict for return
                data = validated_instance.model_dump()
            except Exception as e:
                raise BadRequestError(
                    "F00.101",
                    f"Element data validation failed: {str(e)}",
                    str(e)
                )
        
        # Additional custom validation can be implemented in subclasses
        return cls._validate_custom(data)

    @classmethod
    def _validate_custom(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Override in subclasses for custom validation logic.
        
        Args:
            data: The element data to validate
            
        Returns:
            Validated data dictionary
        """
        return data

    @classmethod
    def to_element_type_dict(cls) -> Dict[str, Any]:
        """
        Convert this element type to a dictionary suitable for ElementType table.
        
        Returns:
            Dictionary with keys: type_key, type_name, desc, element_schema, attrs
        """
        return {
            "type_key": cls.type_key,
            "type_name": cls.type_name,
            "desc": cls.desc,
            "element_schema": cls.element_schema.__name__ if cls.element_schema else None,  # Store class name
            "attrs": cls.attrs,
        }


# Create registry for element types
ElementTypeRegistry = ClassRegistry(BaseElementType)


def register_element_type(type_key: Optional[str] = None):
    """
    Decorator to register an element type.
    
    Usage:
        @register_element_type("text-input")
        class TextInputElement(BaseElementType):
            type_key = "text-input"
            type_name = "Text Input"
            ...
    """
    return ElementTypeRegistry.register(type_key)


# Convenience function to get all registered element types
def get_all_element_types():
    """Get all registered element types"""
    return ElementTypeRegistry.get_registry()


# Convenience function to get element type by key
def get_element_type(type_key: str) -> type:
    """Get element type class by type_key"""
    return ElementTypeRegistry.get(type_key)


# Convenience function to populate ElementType table
async def populate_element_type_table(statemgr, element_type_class: type = None):
    """
    Populate ElementType table with registered element types.
    
    Args:
        statemgr: The state manager for database operations
        element_type_class: Optional specific element type class to populate.
                          If None, populates all registered types.
    """
    if element_type_class:
        element_types = [element_type_class]
    else:
        element_types = ElementTypeRegistry.values()
    
    for element_type_cls in element_types:
        element_type_dict = element_type_cls.to_element_type_dict()
        
        # Check if element type already exists
        existing = await statemgr.query(
            "element_type",
            where={"type_key": element_type_dict["type_key"]},
            limit=1
        )
        
        if not existing:
            # Create new element type record
            element_type_record = statemgr.create("element_type", **element_type_dict)
            await statemgr.insert(element_type_record)


class ElementDataManager(DataAccessManager):
    """Data manager for element data storage in DB_SCHEMA_ELEMENT"""
    __connector__ = FormConnector
    __automodel__ = True


class ElementBaseSchema(FormConnector.__data_schema_base__, DomainSchema):
    __abstract__ = True


# --- Helper Functions for Foreign Keys ---
def data_element_fk(constraint_name, **kwargs):
    """Create a foreign key reference to the data_element table"""
    # NOTE: For cross-schema foreign keys with separate metadata, we define the column
    # without a ForeignKey constraint initially. The constraint will be created manually
    # after both schemas are created (see schema_setup.py)
    return sa.Column(pg.UUID, nullable=False, **kwargs)


def data_form_fk(constraint_name, **kwargs):
    """Create a foreign key reference to the data_form table"""
    # NOTE: For cross-schema foreign keys with separate metadata, we define the column
    # without a ForeignKey constraint initially. The constraint will be created manually
    # after both schemas are created (see schema_setup.py)
    return sa.Column(pg.UUID, nullable=False, **kwargs)


# --- Models ---
class FormInstance(ElementBaseSchema):
    """Instances of forms containing element data"""
    __tablename__ = "form_instance"
    __table_args__ = (
        sa.UniqueConstraint('form_id', 'instance_key', name='uq_form_instance_key'), {
            'schema': DB_SCHEMA_ELEMENT,
        }
    )

    form_id = data_form_fk("form_instance_form_id")
    instance_key = sa.Column(sa.String, nullable=False)
    instance_name = sa.Column(sa.String, nullable=True)
    locked = sa.Column(sa.Boolean, nullable=False, default=False)  # Lock from further editing
    attrs = sa.Column(FluviusJSONField, nullable=True)  # Instance-level configuration
    owner_id = sa.Column(pg.UUID, nullable=True)
    organization_id = sa.Column(sa.String, nullable=True)


class ElementDataMeta(DataModel):
    """
    Metadata for ElementData schemas.
    
    Each ElementData subclass can define a Meta class with:
    - type_key: Unique identifier for the element type (required)
    - type_name: Human-readable name (required)
    - desc: Description (optional)
    - element_schema: DataModel class for validation (optional)
    - attrs: Additional configuration (optional)
    """
    type_key: str
    type_name: str
    desc: Optional[str] = None
    element_schema: Optional[Type[DataModel]] = None  # DataModel class for validation
    attrs: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert Meta to dictionary suitable for ElementType table"""
        return {
            "type_key": self.type_key,
            "type_name": self.type_name,
            "desc": self.desc,
            "element_schema": self.element_schema.__name__ if self.element_schema else None,  # Store class name
            "attrs": self.attrs,
        }


class ElementData(ElementBaseSchema):
    """
    Base schema for storing element data.
    
    Element types are created by inheriting this class with a new table name
    and updated structure. Each subclass must define a Meta class containing
    element type metadata.
    
    Example:
        class TextInputData(DataModel):
            value: str
        
        class TextInputElementData(ElementData):
            __tablename__ = "text_input_element_data"
            __table_args__ = (
                sa.UniqueConstraint('form_instance_id', 'element_id'),
                {'schema': DB_SCHEMA_ELEMENT}
            )
            
            class Meta:
                type_key = "text-input"
                type_name = "Text Input"
                desc = "A text input element"
                element_schema = TextInputData  # DataModel class for validation
            
            # Add custom columns as needed
            custom_field = sa.Column(sa.String, nullable=True)
    """
    __abstract__ = True
    __tablename__ = "element_data"
    __table_args__ = (
        sa.UniqueConstraint('form_instance_id', 'element_id', name='uq_element_data_instance'),
        {
            'schema': DB_SCHEMA_ELEMENT,
        }
    )

    form_instance_id = sa.Column(
        pg.UUID,
        sa.ForeignKey(
            f'{DB_SCHEMA_ELEMENT}.form_instance._id',
            ondelete='CASCADE',
            onupdate='CASCADE',
            name='fk_element_data_form_instance'
        ),
        nullable=False
    )
    element_id = data_element_fk("element_data_element_id")
    data = sa.Column(FluviusJSONField, nullable=False)  # Validated element data
    attrs = sa.Column(FluviusJSONField, nullable=True)  # Additional metadata
    
    def __init_subclass__(cls, **kwargs):
        """Convert Meta class to ElementDataMeta instance and register schema"""
        super().__init_subclass__(**kwargs)
        
        if cls.__dict__.get('__abstract__'):
            return
        
        if not hasattr(cls, 'Meta'):
            raise BadRequestError(
                "F00.102",
                f"ElementData subclass {cls.__name__} must define a Meta class",
                None
            )
        
        # Convert Meta class to ElementDataMeta instance
        meta_cls = cls.Meta
        cls.Meta = ElementDataMeta.create(meta_cls, defaults={
            'type_key': getattr(meta_cls, 'type_key', None),
            'type_name': getattr(meta_cls, 'type_name', cls.__name__),
        })
        
        # Validate required fields
        if not cls.Meta.type_key:
            raise BadRequestError(
                "F00.103",
                f"ElementData subclass {cls.__name__} Meta must define type_key",
                None
            )
        
        if not cls.Meta.type_name:
            raise BadRequestError(
                "F00.104",
                f"ElementData subclass {cls.__name__} Meta must define type_name",
                None
            )
        
        # Automatically register the schema in the registry using type_key
        # Use register() method with the type_key
        ElementDataSchemaRegistry.register(cls.Meta.type_key)(cls)
    
    @classmethod
    def get_meta(cls) -> Optional[ElementDataMeta]:
        """
        Get the Meta object from this ElementData subclass.
        
        Returns:
            ElementDataMeta instance if Meta exists, None otherwise
        """
        return getattr(cls, 'Meta', None)
    
    @classmethod
    def validate_element_data(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate element data against this element type's schema.
        
        Args:
            data: The element data to validate
            
        Returns:
            Validated data dictionary
            
        Raises:
            BadRequestError: If data doesn't match the schema or Meta is missing
        """
        meta = cls.get_meta()
        if not meta:
            raise BadRequestError(
                "F00.102",
                f"ElementData subclass {cls.__name__} must define a Meta class",
                None
            )
        
        if meta.element_schema:
            # Use DataModel validation if element_schema is provided
            try:
                # Instantiate the DataModel class with the data to validate
                validated_instance = meta.element_schema(**data)
                # Convert back to dict for return
                return validated_instance.model_dump()
            except Exception as e:
                raise BadRequestError(
                    "F00.101",
                    f"Element data validation failed: {str(e)}",
                    str(e)
                )
        
        return data


# Registry for ElementData subclasses
# Registration happens automatically via __init_subclass__
ElementDataSchemaRegistry = ClassRegistry(ElementData)

# Register ElementData in FormConnector's schema registry
# This allows ElementDataManager to query the element_data table
# Even though ElementData is abstract, it represents a real table that needs to be queryable
FormConnector.register_schema(ElementData, name="element_data")


def get_element_data_schema(type_key: str) -> Optional[type]:
    """
    Get ElementData schema class by type_key.
    
    Args:
        type_key: The element type key
        
    Returns:
        ElementData subclass or None if not found
    """
    try:
        return ElementDataSchemaRegistry.get(type_key)
    except RuntimeError:
        return None


def get_all_element_data_schemas() -> Dict[str, type]:
    """
    Get all registered ElementData schemas.
    
    Returns:
        Dictionary mapping type_key to ElementData subclass
    """
    return dict(ElementDataSchemaRegistry.items())


async def populate_element_type_table_from_schemas(statemgr):
    """
    Populate ElementType table from registered ElementData schemas.
    
    Args:
        statemgr: The state manager for database operations
    """
    for schema_class in ElementDataSchemaRegistry.values():
        meta = schema_class.get_meta()
        if not meta:
            continue
        
        element_type_dict = meta.to_dict()
        
        # Check if element type already exists
        existing = await statemgr.query(
            "element_type",
            where={"type_key": element_type_dict["type_key"]},
            limit=1
        )
        
        if not existing:
            # Create new element type record
            element_type_record = statemgr.create("element_type", **element_type_dict)
            await statemgr.insert(element_type_record)

