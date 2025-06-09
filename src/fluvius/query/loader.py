"""
Dynamic QueryResource Loader

This module provides functionality to load QueryResource definitions from YAML or JSON files
and dynamically create QueryResource classes.
"""

import os
import json
import yaml
from pathlib import Path
from typing import Union, Dict, Any, Generator, Optional, List, Literal
from pydantic import BaseModel, Field, ValidationError, field_validator, ConfigDict

from .resource import QueryResource, QueryResourceMeta
from .field import (
    QueryField, StringField, IntegerField, DateField, DateTimeField, 
    EnumField, UUIDField, ArrayField, BooleanField, FloatField, TextSearchField
)
from . import logger


# Field type mapping for dynamic creation
FIELD_TYPE_MAPPING = {
    'string': StringField,
    'text': StringField,
    'integer': IntegerField,
    'int': IntegerField,
    'date': DateField,
    'datetime': DateTimeField,
    'timestamp': DateTimeField,
    'enum': EnumField,
    'uuid': UUIDField,
    'array': ArrayField,
    'list': ArrayField,
    'boolean': BooleanField,
    'bool': BooleanField,
    'float': FloatField,
    'decimal': FloatField,
    'textsearch': TextSearchField,
    'fulltext': TextSearchField,
}

# Valid field types for validation
FieldType = Literal[
    'string', 'text', 'integer', 'int', 'date', 'datetime', 'timestamp',
    'enum', 'uuid', 'array', 'list', 'boolean', 'bool', 'float', 'decimal',
    'textsearch', 'fulltext'
]


class FieldConfig(BaseModel):
    """Pydantic model for field configuration validation"""
    type: FieldType = Field(..., description="Field type")
    label: Optional[str] = Field(None, description="Human-readable label")
    sortable: bool = Field(True, description="Whether field is sortable")
    hidden: bool = Field(False, description="Whether field is hidden")
    identifier: bool = Field(False, description="Whether this is the identifier field")
    source: Optional[str] = Field(None, description="Source column name")


class ResourceMetaConfig(BaseModel):
    """Pydantic model for resource meta configuration validation"""
    allow_item_view: bool = Field(True, description="Allow single item queries")
    allow_list_view: bool = Field(True, description="Allow list queries") 
    allow_meta_view: bool = Field(True, description="Allow metadata queries")
    auth_required: bool = Field(True, description="Require authentication")
    select_all: bool = Field(False, description="Select all fields by default")
    default_order: Optional[List[str]] = Field(None, description="Default sort order")
    scope_required: Optional[Dict[str, Any]] = Field(None, description="Required scope")
    scope_optional: Optional[Dict[str, Any]] = Field(None, description="Optional scope")
    soft_delete_query: Optional[str] = Field(None, description="Soft delete query field")
    ignored_params: List[str] = Field(default_factory=list, description="Ignored parameters")


class QueryResourceSpec(BaseModel):
    """Pydantic model for QueryResource specification validation"""
    name: str = Field(..., description="Resource name")
    description: Optional[str] = Field(None, description="Resource description")
    backend_model: Optional[str] = Field(None, description="Backend model name")
    tags: Optional[List[str]] = Field(default_factory=list, description="Resource tags")
    fields: Dict[str, FieldConfig] = Field(..., description="Field configurations")
    meta: Optional[ResourceMetaConfig] = Field(None, description="Meta configuration")
    
    @field_validator('name')
    @classmethod
    def name_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Resource name cannot be empty')
        return v.strip()
    
    @field_validator('fields')
    @classmethod
    def must_have_identifier_field(cls, v):
        """Ensure at least one field is marked as identifier"""
        identifier_fields = [field_name for field_name, config in v.items() if config.identifier]
        if not identifier_fields:
            raise ValueError('At least one field must be marked as identifier')
        if len(identifier_fields) > 1:
            raise ValueError(f'Only one field can be marked as identifier, found: {identifier_fields}')
        return v


class ResourcesConfig(BaseModel):
    """Pydantic model for the root configuration containing multiple resources"""
    resources: Dict[str, QueryResourceSpec] = Field(..., description="Resource specifications")
    
    @field_validator('resources')
    @classmethod
    def resources_must_not_be_empty(cls, v):
        if not v:
            raise ValueError('At least one resource must be defined')
        return v


class ConfigFile(BaseModel):
    """Pydantic model for configuration file validation - handles both formats"""
    # Allow both direct resource definitions and nested under 'resources' key
    resources: Optional[Dict[str, QueryResourceSpec]] = Field(None, description="Resources under 'resources' key")
    
    model_config = ConfigDict(extra='allow')  # Allow additional fields for direct resource definitions
    
    def model_post_init(self, __context):
        """Post-initialization validation to handle both nested and flat formats"""
        # If we have resources under 'resources' key, we're good
        if self.resources:
            return
        
        # Otherwise, try to parse root-level fields as resources
        resources = {}
        # Get all model fields that aren't 'resources'
        for field_name in self.__class__.model_fields:
            if field_name != 'resources':
                value = getattr(self, field_name, None)
                if value is not None and isinstance(value, dict):
                    try:
                        # Try to parse as QueryResourceSpec - this will validate
                        resources[field_name] = QueryResourceSpec.model_validate(value)
                    except ValidationError as e:
                        # Re-raise with more context
                        raise ValueError(f"Invalid resource '{field_name}': {e}")
        
        # Also check for any extra fields that might be resources
        if hasattr(self, '__pydantic_extra__'):
            for key, value in self.__pydantic_extra__.items():
                if isinstance(value, dict):
                    try:
                        resources[key] = QueryResourceSpec.model_validate(value)
                    except ValidationError as e:
                        raise ValueError(f"Invalid resource '{key}': {e}")
        
        if not resources:
            raise ValueError('No valid resources found in configuration')
        
        # Store the parsed resources
        self.resources = resources
    
    def get_resources(self) -> Dict[str, QueryResourceSpec]:
        """Get resources - they should already be validated by model_post_init"""
        if not self.resources:
            raise ValueError('No resources available')
        return self.resources


def load_config_file(file_path: Union[str, Path]) -> ConfigFile:
    """
    Load and validate configuration from a YAML or JSON file using Pydantic.
    
    Args:
        file_path: Path to the configuration file
        
    Returns:
        ConfigFile: Validated configuration object
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the file format is not supported or invalid
        ValidationError: If the configuration doesn't match the schema
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            if file_path.suffix.lower() in ('.yml', '.yaml'):
                raw_data = yaml.safe_load(f)
            elif file_path.suffix.lower() == '.json':
                raw_data = json.load(f)
            else:
                raise ValueError(f"Unsupported file format: {file_path.suffix}")
                
    except (yaml.YAMLError, json.JSONDecodeError) as e:
        raise ValueError(f"Error parsing {file_path}: {e}")
    
    try:
        # Validate using Pydantic
        return ConfigFile.model_validate(raw_data)
    except ValidationError as e:
        raise ValueError(f"Configuration validation failed for {file_path}: {e}")


def create_query_field(field_name: str, field_config: FieldConfig) -> QueryField:
    """
    Create a QueryField instance from validated Pydantic configuration.
    
    Args:
        field_name: Name of the field
        field_config: Validated FieldConfig instance
        
    Returns:
        QueryField instance
    """
    # Generate label if not provided
    label = field_config.label or field_name.replace('_', ' ').title()
    
    field_class = FIELD_TYPE_MAPPING[field_config.type]
    
    # Extract field parameters
    field_params = {
        'label': label,
        'sortable': field_config.sortable,
        'hidden': field_config.hidden,
        'identifier': field_config.identifier,
    }
    
    # Add source if provided
    if field_config.source:
        field_params['source'] = field_config.source
    
    return field_class(**field_params)


def create_dynamic_query_resource(spec: QueryResourceSpec) -> type:
    """
    Create a dynamic QueryResource class from validated specification.
    
    Args:
        spec: Validated QueryResourceSpec containing the resource definition
        
    Returns:
        Dynamically created QueryResource class
    """
    # Create the class attributes dictionary
    class_attrs = {}
    
    # Add fields
    for field_name, field_config in spec.fields.items():
        class_attrs[field_name] = create_query_field(field_name, field_config)
    
    # Create Meta class attributes
    meta_attrs = {
        'name': spec.name,
        'desc': spec.description,
        'backend_model': spec.backend_model,
        'tags': spec.tags,
    }
    
    # Add meta configuration if provided
    if spec.meta:
        meta_dict = spec.meta.model_dump(exclude_none=True)
        meta_attrs.update(meta_dict)
    
    # Remove None values from meta_attrs
    meta_attrs = {k: v for k, v in meta_attrs.items() if v is not None}
    
    # Create Meta class
    meta_class = type('Meta', (QueryResource.Meta,), meta_attrs)
    class_attrs['Meta'] = meta_class
    
    # Add docstring
    class_attrs['__doc__'] = spec.description or f"Dynamic QueryResource for {spec.name}"
    
    # Create the dynamic class
    class_name = f"Dynamic{spec.name.replace('-', '').replace('_', '').title()}QueryResource"
    dynamic_class = type(class_name, (QueryResource,), class_attrs)
    
    return dynamic_class


def parse_resource_spec(resources_dict: Dict[str, QueryResourceSpec], resource_key: str) -> QueryResourceSpec:
    """
    Get a validated resource specification from the resources dictionary.
    
    Args:
        resources_dict: Dictionary of validated QueryResourceSpec instances
        resource_key: Key of the resource in the configuration
        
    Returns:
        QueryResourceSpec instance
        
    Raises:
        KeyError: If resource key is not found
    """
    if resource_key not in resources_dict:
        raise KeyError(f"Resource '{resource_key}' not found in configuration")
    
    return resources_dict[resource_key]


def load_query_resources_from_file(
    file_path: Union[str, Path], 
    resource_keys: Optional[List[str]] = None
) -> Generator[tuple[str, type], None, None]:
    """
    Generator that loads and validates QueryResource classes from a YAML or JSON file.
    
    Args:
        file_path: Path to the configuration file
        resource_keys: Optional list of specific resource keys to load.
                      If None, loads all resources found in the file.
    
    Yields:
        Tuple[str, type]: (resource_identifier, QueryResource_class)
        
    Raises:
        ValidationError: If configuration validation fails
        ValueError: If resource keys are missing or invalid
        
    Example:
        ```python
        for resource_id, resource_class in load_query_resources_from_file('resources.yml'):
            print(f"Loaded resource: {resource_id}")
            query_manager.register_resource_class(resource_id, resource_class)
        ```
    """
    # Load and validate configuration
    config = load_config_file(file_path)
    resources_dict = config.get_resources()
    
    # Determine which resources to load
    if resource_keys is None:
        keys_to_load = list(resources_dict.keys())
    else:
        keys_to_load = resource_keys
        # Validate that all requested keys exist
        missing_keys = set(resource_keys) - set(resources_dict.keys())
        if missing_keys:
            raise ValueError(f"Resource keys not found in config: {missing_keys}")
    
    for resource_key in keys_to_load:
        try:
            spec = parse_resource_spec(resources_dict, resource_key)
            resource_class = create_dynamic_query_resource(spec)
            
            logger.info(f"Dynamically created QueryResource: {resource_key}")
            yield resource_key, resource_class
            
        except Exception as e:
            logger.error(f"Failed to create QueryResource '{resource_key}': {e}")
            raise


def load_query_resources_from_directory(
    directory_path: Union[str, Path],
    pattern: str = "*.yml",
    recursive: bool = False
) -> Generator[tuple[str, str, type], None, None]:
    """
    Generator that loads QueryResource classes from all files in a directory.
    
    Args:
        directory_path: Path to the directory containing configuration files
        pattern: File pattern to match (default: "*.yml")
        recursive: Whether to search recursively in subdirectories
    
    Yields:
        Tuple[str, str, type]: (file_path, resource_identifier, QueryResource_class)
        
    Example:
        ```python
        for file_path, resource_id, resource_class in load_query_resources_from_directory('./configs'):
            print(f"Loaded {resource_id} from {file_path}")
            query_manager.register_resource_class(resource_id, resource_class)
        ```
    """
    directory_path = Path(directory_path)
    
    if not directory_path.exists():
        raise FileNotFoundError(f"Directory not found: {directory_path}")
    
    if not directory_path.is_dir():
        raise ValueError(f"Path is not a directory: {directory_path}")
    
    # Find files matching the pattern
    if recursive:
        files = directory_path.rglob(pattern)
    else:
        files = directory_path.glob(pattern)
    
    for file_path in files:
        try:
            for resource_id, resource_class in load_query_resources_from_file(file_path):
                yield str(file_path), resource_id, resource_class
        except Exception as e:
            logger.error(f"Failed to load resources from {file_path}: {e}")
            # Continue with other files instead of raising
            continue


def create_sample_config() -> Dict[str, Any]:
    """
    Create a sample configuration dictionary that validates with our Pydantic models.
    
    Returns:
        Dict containing sample QueryResource configurations
    """
    return {
        "resources": {
            "user-profile": {
                "name": "User Profile",
                "description": "Query user profile information",
                "backend_model": "user_profile",
                "tags": ["user", "profile"],
                "fields": {
                    "_id": {
                        "type": "uuid",
                        "label": "User ID",
                        "identifier": True
                    },
                    "username": {
                        "type": "string",
                        "label": "Username",
                        "sortable": True
                    },
                    "email": {
                        "type": "string",
                        "label": "Email Address"
                    },
                    "created_at": {
                        "type": "datetime",
                        "label": "Created Date",
                        "sortable": True
                    },
                    "status": {
                        "type": "enum",
                        "label": "Account Status"
                    }
                },
                "meta": {
                    "allow_item_view": True,
                    "allow_list_view": True,
                    "select_all": False
                }
            },
            "order-history": {
                "name": "Order History",
                "description": "Query order history data",
                "backend_model": "orders",
                "tags": ["orders", "commerce"],
                "fields": {
                    "order_id": {
                        "type": "uuid",
                        "label": "Order ID",
                        "identifier": True
                    },
                    "customer_name": {
                        "type": "string",  
                        "label": "Customer Name"
                    },
                    "order_total": {
                        "type": "float",
                        "label": "Order Total"
                    },
                    "order_date": {
                        "type": "date",
                        "label": "Order Date"
                    },
                    "status": {
                        "type": "enum",
                        "label": "Order Status"
                    }
                }
            }
        }
    }


def save_sample_config(file_path: Union[str, Path], format: str = 'yaml') -> None:
    """
    Save a sample configuration to a file.
    
    Args:
        file_path: Path where to save the sample configuration
        format: Format to save in ('yaml' or 'json')
    """
    config = create_sample_config()
    file_path = Path(file_path)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        if format.lower() == 'yaml':
            yaml.dump(config, f, default_flow_style=False, indent=2)
        elif format.lower() == 'json':
            json.dump(config, f, indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    logger.info(f"Sample configuration saved to: {file_path}") 