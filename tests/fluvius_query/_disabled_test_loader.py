"""
Tests for the QueryResource loader functionality.
"""

import pytest
import tempfile
import json
import yaml
from pathlib import Path

from fluvius.query.loader import (
    load_config_file,
    create_query_field,
    create_dynamic_query_resource,
    parse_resource_spec,
    load_query_resources_from_file,
    load_query_resources_from_directory,
    create_sample_config,
    save_sample_config,
    QueryResourceSpec,
    FieldConfig,
    ResourceMetaConfig,
    ConfigFile,
    FIELD_TYPE_MAPPING
)
from pydantic import ValidationError
from fluvius.query.resource import QueryResource
from fluvius.query.field import StringField, UUIDField, IntegerField, QueryField


def test_load_config_file_yaml():
    """Test loading YAML configuration file with valid resource"""
    config_data = {
        'resources': {
            'test-resource': {
                'name': 'Test Resource',
                'fields': {
                    '_id': {
                        'type': 'uuid',
                        'identifier': True
                    }
                }
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        yaml.dump(config_data, f)
        temp_path = f.name
    
    try:
        config = load_config_file(temp_path)
        assert isinstance(config, ConfigFile)
        resources = config.get_resources()
        assert 'test-resource' in resources
        assert isinstance(resources['test-resource'], QueryResourceSpec)
    finally:
        Path(temp_path).unlink()


def test_load_config_file_json():
    """Test loading JSON configuration file with valid resource"""
    config_data = {
        'resources': {
            'test-resource': {
                'name': 'Test Resource',
                'fields': {
                    '_id': {
                        'type': 'uuid',
                        'identifier': True
                    }
                }
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config_data, f)
        temp_path = f.name
    
    try:
        config = load_config_file(temp_path)
        assert isinstance(config, ConfigFile)
        resources = config.get_resources()
        assert 'test-resource' in resources
        assert isinstance(resources['test-resource'], QueryResourceSpec)
    finally:
        Path(temp_path).unlink()


def test_load_config_file_invalid_format():
    """Test loading file with unsupported format"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write('some text')
        temp_path = f.name
    
    try:
        with pytest.raises(ValueError, match="Unsupported file format"):
            load_config_file(temp_path)
    finally:
        Path(temp_path).unlink()


def test_load_config_file_not_found():
    """Test loading non-existent file"""
    with pytest.raises(FileNotFoundError):
        load_config_file('/nonexistent/file.yml')


def test_create_query_field_string():
    """Test creating a string field"""
    field_config = FieldConfig(
        type='string',
        label='Test Field',
        sortable=True,
        identifier=False
    )
    
    field = create_query_field('test_field', field_config)
    assert isinstance(field, StringField)
    assert field.label == 'Test Field'
    assert field.sortable is True
    assert field.identifier is False


def test_create_query_field_uuid_identifier():
    """Test creating a UUID identifier field"""
    field_config = FieldConfig(
        type='uuid',
        label='ID Field',
        identifier=True
    )
    
    field = create_query_field('id_field', field_config)
    assert isinstance(field, UUIDField)
    assert field.label == 'ID Field'
    assert field.identifier is True


def test_create_query_field_default_label():
    """Test creating field with auto-generated label"""
    field_config = FieldConfig(type='string')
    
    field = create_query_field('test_field_name', field_config)
    assert field.label == 'Test Field Name'  # Converted from snake_case


def test_create_query_field_invalid_type():
    """Test creating field with invalid type"""
    with pytest.raises(ValidationError):
        # This should fail at the Pydantic validation level
        FieldConfig(type='invalid_type')


def test_pydantic_validation_missing_identifier():
    """Test Pydantic validation fails when no identifier field is present"""
    with pytest.raises(ValidationError, match="At least one field must be marked as identifier"):
        QueryResourceSpec(
            name="Test Resource",
            fields={
                "name": FieldConfig(type="string", identifier=False)
            }
        )


def test_pydantic_validation_multiple_identifiers():
    """Test Pydantic validation fails when multiple identifier fields are present"""
    with pytest.raises(ValidationError, match="Only one field can be marked as identifier"):
        QueryResourceSpec(
            name="Test Resource",
            fields={
                "id1": FieldConfig(type="uuid", identifier=True),
                "id2": FieldConfig(type="uuid", identifier=True)
            }
        )


def test_pydantic_validation_empty_name():
    """Test Pydantic validation fails with empty resource name"""
    with pytest.raises(ValidationError, match="Resource name cannot be empty"):
        QueryResourceSpec(
            name="   ",  # Empty/whitespace name
            fields={
                "_id": FieldConfig(type="uuid", identifier=True)
            }
        )


def test_config_file_validation_invalid_structure():
    """Test ConfigFile validation with invalid structure"""
    invalid_config_data = {
        "invalid_resource": {
            "name": "Test",
            "fields": {}  # Missing identifier field - this should fail validation
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        yaml.dump(invalid_config_data, f)
        temp_path = f.name
    
    try:
        with pytest.raises(ValueError, match="Configuration validation failed"):
            load_config_file(temp_path)
    finally:
        Path(temp_path).unlink()


def test_field_config_defaults():
    """Test FieldConfig default values"""
    field_config = FieldConfig(type="string")
    
    assert field_config.type == "string"
    assert field_config.label is None
    assert field_config.sortable is True
    assert field_config.hidden is False
    assert field_config.identifier is False
    assert field_config.source is None


def test_resource_meta_config_defaults():
    """Test ResourceMetaConfig default values"""
    meta_config = ResourceMetaConfig()
    
    assert meta_config.allow_item_view is True
    assert meta_config.allow_list_view is True
    assert meta_config.allow_meta_view is True
    assert meta_config.auth_required is True
    assert meta_config.select_all is False
    assert meta_config.default_order is None
    assert meta_config.ignored_params == []


def test_create_dynamic_query_resource():
    """Test creating a dynamic QueryResource class"""
    spec = QueryResourceSpec(
        name="Test Resource",
        description="A test resource",
        backend_model="test_model",
        tags=["test"],
        fields={
            "_id": FieldConfig(
                type="uuid",
                label="ID",
                identifier=True
            ),
            "name": FieldConfig(
                type="string",
                label="Name"
            )
        },
        meta=ResourceMetaConfig(
            allow_item_view=True,
            select_all=False
        )
    )
    
    resource_class = create_dynamic_query_resource(spec)
    
    # Check that it's a QueryResource subclass
    assert issubclass(resource_class, QueryResource)
    
    # Check Meta attributes
    assert resource_class.Meta.name == "Test Resource"
    assert resource_class.Meta.desc == "A test resource"
    assert resource_class.Meta.backend_model == "test_model"
    assert resource_class.Meta.tags == ["test"]
    assert resource_class.Meta.allow_item_view is True
    assert resource_class.Meta.select_all is False
    
    # Check docstring
    assert "A test resource" in resource_class.__doc__


def test_parse_resource_spec():
    """Test parsing resource specification from validated config"""
    # Create validated resource specs
    resources_dict = {
        "test-resource": QueryResourceSpec(
            name="Test Resource",
            description="Test description", 
            backend_model="test_model",
            fields={
                "id": FieldConfig(type="uuid", identifier=True)
            }
        )
    }
    
    spec = parse_resource_spec(resources_dict, "test-resource")
    
    assert spec.name == "Test Resource"
    assert spec.description == "Test description"
    assert spec.backend_model == "test_model"
    assert spec.fields["id"].type == "uuid"


def test_load_query_resources_from_file():
    """Test loading QueryResources from a YAML file"""
    config_data = {
        "resources": {
            "user-query": {
                "name": "User Query",
                "description": "Query users",
                "fields": {
                    "_id": {
                        "type": "uuid",
                        "identifier": True
                    },
                    "username": {
                        "type": "string",
                        "label": "Username"
                    }
                }
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        yaml.dump(config_data, f)
        temp_path = f.name
    
    try:
        resources = list(load_query_resources_from_file(temp_path))
        
        assert len(resources) == 1
        resource_id, resource_class = resources[0]
        
        assert resource_id == "user-query"
        assert issubclass(resource_class, QueryResource)
        assert resource_class.Meta.name == "User Query"
        assert resource_class.Meta.desc == "Query users"
        
    finally:
        Path(temp_path).unlink()


def test_load_query_resources_from_file_specific_keys():
    """Test loading specific QueryResources from a file"""
    config_data = {
        "resource1": {
            "name": "Resource 1", 
            "fields": {"_id": {"type": "uuid", "identifier": True}}
        },
        "resource2": {
            "name": "Resource 2", 
            "fields": {"_id": {"type": "uuid", "identifier": True}}
        },
        "resource3": {
            "name": "Resource 3", 
            "fields": {"_id": {"type": "uuid", "identifier": True}}
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        yaml.dump(config_data, f)
        temp_path = f.name
    
    try:
        resources = list(load_query_resources_from_file(temp_path, resource_keys=["resource1", "resource3"]))
        
        assert len(resources) == 2
        resource_ids = [r[0] for r in resources]
        assert "resource1" in resource_ids
        assert "resource3" in resource_ids
        assert "resource2" not in resource_ids
        
    finally:
        Path(temp_path).unlink()


def test_load_query_resources_from_file_missing_keys():
    """Test loading QueryResources with missing keys"""
    config_data = {
        "resource1": {
            "name": "Resource 1", 
            "fields": {"_id": {"type": "uuid", "identifier": True}}
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        yaml.dump(config_data, f)
        temp_path = f.name
    
    try:
        with pytest.raises(ValueError, match="Resource keys not found"):
            list(load_query_resources_from_file(temp_path, resource_keys=["resource1", "nonexistent"]))
            
    finally:
        Path(temp_path).unlink()


def test_load_query_resources_from_directory():
    """Test loading QueryResources from a directory"""
    config_data = {
        "test-resource": {
            "name": "Test Resource",
            "fields": {
                "_id": {"type": "uuid", "identifier": True}
            }
        }
    }
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a YAML file in the directory
        yaml_file = Path(temp_dir) / "test.yml"
        with open(yaml_file, 'w') as f:
            yaml.dump(config_data, f)
        
        # Create a JSON file as well
        json_file = Path(temp_dir) / "test.json"
        with open(json_file, 'w') as f:
            json.dump(config_data, f)
        
        # Load only YAML files
        resources = list(load_query_resources_from_directory(temp_dir, pattern="*.yml"))
        
        assert len(resources) == 1
        file_path, resource_id, resource_class = resources[0]
        
        assert Path(file_path).name == "test.yml"
        assert resource_id == "test-resource"
        assert issubclass(resource_class, QueryResource)


def test_create_sample_config():
    """Test creating sample configuration"""
    config = create_sample_config()
    
    assert "resources" in config
    assert "user-profile" in config["resources"]
    assert "order-history" in config["resources"]
    
    user_profile = config["resources"]["user-profile"]
    assert user_profile["name"] == "User Profile"
    assert "fields" in user_profile
    assert "_id" in user_profile["fields"]


def test_save_sample_config_yaml():
    """Test saving sample configuration as YAML"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        temp_path = f.name
    
    try:
        save_sample_config(temp_path, format='yaml')
        
        # Verify the file was created and can be loaded
        with open(temp_path, 'r') as f:
            loaded_config = yaml.safe_load(f)
        
        assert "resources" in loaded_config
        assert "user-profile" in loaded_config["resources"]
        
    finally:
        Path(temp_path).unlink()


def test_save_sample_config_json():
    """Test saving sample configuration as JSON"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name
    
    try:
        save_sample_config(temp_path, format='json')
        
        # Verify the file was created and can be loaded
        with open(temp_path, 'r') as f:
            loaded_config = json.load(f)
        
        assert "resources" in loaded_config
        assert "user-profile" in loaded_config["resources"]
        
    finally:
        Path(temp_path).unlink()


def test_save_sample_config_invalid_format():
    """Test saving sample configuration with invalid format"""
    with tempfile.NamedTemporaryFile(delete=False) as f:
        temp_path = f.name
    
    try:
        with pytest.raises(ValueError, match="Unsupported format"):
            save_sample_config(temp_path, format='xml')
    finally:
        Path(temp_path).unlink()


def test_field_type_mapping_coverage():
    """Test that all expected field types are mapped"""
    expected_types = [
        'string', 'text', 'integer', 'int', 'date', 'datetime',
        'timestamp', 'enum', 'uuid', 'array', 'list', 'boolean',
        'bool', 'float', 'decimal', 'textsearch', 'fulltext'
    ]
    
    for field_type in expected_types:
        assert field_type in FIELD_TYPE_MAPPING
        field_class = FIELD_TYPE_MAPPING[field_type]
        assert issubclass(field_class, QueryField) or hasattr(field_class, '_ops')


def test_integration_full_workflow():
    """Integration test for the full workflow"""
    # Create a configuration
    config_data = {
        "resources": {
            "product-catalog": {
                "name": "Product Catalog",
                "description": "Browse product catalog",
                "backend_model": "products",
                "tags": ["products", "catalog"],
                "fields": {
                    "product_id": {
                        "type": "uuid",
                        "label": "Product ID",
                        "identifier": True
                    },
                    "name": {
                        "type": "string",
                        "label": "Product Name"
                    },
                    "price": {
                        "type": "float",
                        "label": "Price"
                    },
                    "category": {
                        "type": "enum",
                        "label": "Category"
                    },
                    "created_at": {
                        "type": "datetime",
                        "label": "Created Date"
                    },
                    "in_stock": {
                        "type": "boolean",
                        "label": "In Stock"
                    }
                },
                "meta": {
                    "allow_item_view": True,
                    "allow_list_view": True,
                    "select_all": False
                }
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        yaml.dump(config_data, f)
        temp_path = f.name
    
    try:
        # Load the resources
        resources = list(load_query_resources_from_file(temp_path))
        
        assert len(resources) == 1
        resource_id, resource_class = resources[0]
        
        # Verify the resource
        assert resource_id == "product-catalog"
        assert issubclass(resource_class, QueryResource)
        
        # Create an instance to test the fields
        resource_instance = resource_class()
        
        # Check that fields are properly created
        assert hasattr(resource_instance, 'product_id')
        assert hasattr(resource_instance, 'name')
        assert hasattr(resource_instance, 'price')
        assert hasattr(resource_instance, 'category')
        assert hasattr(resource_instance, 'created_at')
        assert hasattr(resource_instance, 'in_stock')
        
        # Check Meta attributes
        assert resource_instance.Meta.name == "Product Catalog"
        assert resource_instance.Meta.desc == "Browse product catalog"
        assert resource_instance.Meta.backend_model == "products"
        assert resource_instance.Meta.tags == ["products", "catalog"]
        assert resource_instance.Meta.allow_item_view is True
        assert resource_instance.Meta.select_all is False
        
    finally:
        Path(temp_path).unlink() 