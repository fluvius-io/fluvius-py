"""
Pydantic to SQLAlchemy Mapper

This module provides utilities to generate SQLAlchemy schema definitions
from Pydantic models, enabling dynamic table creation based on Pydantic
model definitions.

Usage:
    from pydantic import BaseModel
    from fluvius.dform.mapper import PydanticSQLAlchemyMapper
    
    class UserData(BaseModel):
        name: str
        email: str
        age: int
        is_active: bool = True
        metadata: dict = {}
    
    # Generate SQLAlchemy table class
    mapper = PydanticSQLAlchemyMapper(base_class=FormDataBaseSchema)
    UserTable = mapper.create_table_class(UserData, "user_data")
"""
import uuid
from datetime import datetime, date, time
from decimal import Decimal
from enum import Enum
from typing import (
    Any, Dict, List, Optional, Type, Union, 
    get_origin, get_args, get_type_hints
)

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg
from pydantic import BaseModel
from pydantic.fields import FieldInfo

from fluvius.data import FluviusJSONField


# Type mapping from Python/Pydantic types to SQLAlchemy column types
PYTHON_TO_SQLA_TYPE = {
    # Basic types
    str: sa.String,
    int: sa.Integer,
    float: sa.Float,
    bool: sa.Boolean,
    bytes: sa.LargeBinary,
    
    # Decimal
    Decimal: sa.Numeric,
    
    # Date/Time types
    datetime: sa.DateTime(timezone=True),
    date: sa.Date,
    time: sa.Time,
    
    # UUID
    uuid.UUID: pg.UUID,
    
    # Complex types -> JSONB
    dict: FluviusJSONField,
    list: FluviusJSONField,
    Dict: FluviusJSONField,
    List: FluviusJSONField,
}


class PydanticSQLAlchemyMapper:
    """
    Maps Pydantic models to SQLAlchemy table definitions.
    
    This mapper converts Pydantic model fields to SQLAlchemy columns,
    handling type conversions, nullable fields, and default values.
    """
    
    def __init__(
        self, 
        base_class: Type = None,
        type_mapping: Dict[Type, Any] = None,
        default_string_length: int = None,
        schema: str = None,
    ):
        """
        Initialize the mapper.
        
        Args:
            base_class: SQLAlchemy declarative base class to inherit from
            type_mapping: Custom type mappings to override defaults
            default_string_length: Default length for String columns (None = unlimited)
        """
        self.base_class = base_class
        self.type_mapping = {**PYTHON_TO_SQLA_TYPE, **(type_mapping or {})}
        self.default_string_length = default_string_length
        self.schema = schema
    
    def get_sqlalchemy_type(self, python_type: Type) -> Any:
        """
        Get the SQLAlchemy column type for a Python type.
        
        Args:
            python_type: Python type annotation
            
        Returns:
            SQLAlchemy column type
        """
        # Check direct mapping first
        if python_type in self.type_mapping:
            return self.type_mapping[python_type]
        
        # Handle generic types (List[...], Dict[...], etc.)
        origin = get_origin(python_type)
        if origin is not None:
            if origin in (list, List):
                return FluviusJSONField
            if origin in (dict, Dict):
                return FluviusJSONField
            if origin is Union:
                # For Optional types, get the non-None type
                args = get_args(python_type)
                non_none_args = [a for a in args if a is not type(None)]
                if non_none_args:
                    return self.get_sqlalchemy_type(non_none_args[0])
        
        # Handle Enum types
        if isinstance(python_type, type) and issubclass(python_type, Enum):
            return sa.String
        
        # Handle nested Pydantic models -> JSONB
        if isinstance(python_type, type) and issubclass(python_type, BaseModel):
            return FluviusJSONField
        
        # Default to JSONB for complex/unknown types
        return FluviusJSONField
    
    def is_nullable(self, field_type: Type, field_info: FieldInfo) -> bool:
        """
        Determine if a field should be nullable.
        
        Args:
            field_type: The field's type annotation
            field_info: Pydantic field info
            
        Returns:
            True if the field should be nullable
        """
        # Check if it's Optional (Union with None)
        origin = get_origin(field_type)
        if origin is Union:
            args = get_args(field_type)
            if type(None) in args:
                return True
        
        # Check if field has a default value
        if field_info.default is not None:
            return True
        if field_info.default_factory is not None:
            return True
            
        return False
    
    def get_default_value(self, field_info: FieldInfo) -> Any:
        """
        Get the default value for a field.
        
        Args:
            field_info: Pydantic field info
            
        Returns:
            Default value or None
        """
        from pydantic_core import PydanticUndefined
        
        if field_info.default is not PydanticUndefined:
            return field_info.default
        return None
    
    def create_column(
        self, 
        field_name: str, 
        field_type: Type, 
        field_info: FieldInfo
    ) -> sa.Column:
        """
        Create a SQLAlchemy Column from a Pydantic field.
        
        Args:
            field_name: Name of the field
            field_type: Type annotation of the field
            field_info: Pydantic field info
            
        Returns:
            SQLAlchemy Column
        """
        sa_type = self.get_sqlalchemy_type(field_type)
        nullable = self.is_nullable(field_type, field_info)
        default = self.get_default_value(field_info)
        
        # Handle String type with optional length
        if sa_type == sa.String and self.default_string_length:
            sa_type = sa.String(self.default_string_length)
        
        # Build column kwargs
        column_kwargs = {
            'nullable': nullable,
        }
        
        # Add default if it's a simple value (not callable)
        if default is not None and not callable(default):
            column_kwargs['default'] = default
        
        return sa.Column(sa_type, **column_kwargs)
    
    def get_columns(self, model: Type[BaseModel]) -> Dict[str, sa.Column]:
        """
        Generate SQLAlchemy columns from a Pydantic model.
        
        Args:
            model: Pydantic model class
            
        Returns:
            Dictionary of field name to SQLAlchemy Column
        """
        columns = {}
        
        for field_name, field_info in model.model_fields.items():
            field_type = field_info.annotation
            columns[field_name] = self.create_column(field_name, field_type, field_info)
        
        return columns
    
    def create_table_class(
        self,
        model: Type[BaseModel],
        table_name: str,
        table_args: tuple = None,
        extra_columns: Dict[str, sa.Column] = None,
    ) -> Type:
        """
        Create a SQLAlchemy table class from a Pydantic model.
        
        Args:
            model: Pydantic model class
            table_name: Name of the database table
            table_args: Additional table arguments (constraints, indexes, etc.)
            extra_columns: Additional columns to add beyond the Pydantic fields
            
        Returns:
            SQLAlchemy declarative class
        """
        if self.base_class is None:
            raise ValueError("base_class must be set to create table classes")
        
        # Build class attributes
        attrs = {
            '__tablename__': table_name,
        }
        
        # Add table args if provided
        if table_args or self.schema:
            args = table_args or ()
            if self.schema:
                if isinstance(args, tuple):
                    args = args + ({'schema': self.schema},)
                else:
                    args = ({'schema': self.schema},)
            attrs['__table_args__'] = args
        
        # Add columns from Pydantic model
        columns = self.get_columns(model)
        attrs.update(columns)
        
        # Add extra columns
        if extra_columns:
            attrs.update(extra_columns)
        
        # Create the class
        class_name = f"{model.__name__}Table"
        return type(class_name, (self.base_class,), attrs)
    
    def create_table(
        self,
        model: Type[BaseModel],
        table_name: str,
        metadata: sa.MetaData,
        extra_columns: List[sa.Column] = None,
    ) -> sa.Table:
        """
        Create a SQLAlchemy Table object from a Pydantic model.
        
        This is useful when you don't need a declarative class.
        
        Args:
            model: Pydantic model class
            table_name: Name of the database table
            metadata: SQLAlchemy MetaData instance
            extra_columns: Additional columns to add
            
        Returns:
            SQLAlchemy Table object
        """
        columns = []
        
        # Add columns from Pydantic model
        for field_name, column in self.get_columns(model).items():
            # Create a new column with the field name
            columns.append(sa.Column(field_name, column.type, nullable=column.nullable))
        
        # Add extra columns
        if extra_columns:
            columns.extend(extra_columns)
        
        return sa.Table(
            table_name,
            metadata,
            *columns,
            schema=self.schema,
        )


def pydantic_to_columns(model: Type[BaseModel]) -> Dict[str, sa.Column]:
    """
    Convenience function to generate SQLAlchemy columns from a Pydantic model.
    
    Args:
        model: Pydantic model class
        
    Returns:
        Dictionary of field name to SQLAlchemy Column
    """
    mapper = PydanticSQLAlchemyMapper()
    return mapper.get_columns(model)


def pydantic_to_table_class(
    model: Type[BaseModel],
    table_name: str,
    base_class: Type,
    table_args: tuple = None,
) -> Type:
    """
    Convenience function to create a SQLAlchemy table class from a Pydantic model.
    
    Args:
        model: Pydantic model class
        table_name: Name of the database table
        base_class: SQLAlchemy declarative base class
        table_args: Additional table arguments
        
    Returns:
        SQLAlchemy declarative class
    """
    mapper = PydanticSQLAlchemyMapper(base_class=base_class)
    return mapper.create_table_class(
        model, 
        table_name, 
        table_args=table_args,
    )

