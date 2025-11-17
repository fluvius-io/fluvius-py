"""
Element Type System

BaseElementType provides a base class for defining element types with validation.
Element types are registered and can be used to populate the ElementType table.
"""
from fluvius.data import DataModel
from fluvius.helper.registry import ClassRegistry
from typing import Optional, Dict, Any, ClassVar
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
    - schema_def: JSON schema for validation (optional)
    - attrs: Additional configuration (optional)
    """
    type_key: ClassVar[str]
    type_name: ClassVar[str]
    desc: ClassVar[Optional[str]] = None
    schema_def: ClassVar[Optional[Dict[str, Any]]] = None
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
        if cls.schema_def:
            # Use JSON schema validation if schema_def is provided
            try:
                from jsonschema import validate, ValidationError
                validate(instance=data, schema=cls.schema_def)
            except ImportError:
                # jsonschema not available, skip validation
                pass
            except Exception as e:
                from fluvius.error import BadRequestError
                raise BadRequestError(
                    "E100-001",
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
            Dictionary with keys: type_key, type_name, desc, schema_def, attrs
        """
        return {
            "type_key": cls.type_key,
            "type_name": cls.type_name,
            "desc": cls.desc,
            "schema_def": cls.schema_def,
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


class ElementData(ElementBaseSchema):
    """Stored data for form elements"""
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

