#!/usr/bin/env python
"""
Demo script showing how to use the QueryResource loader functionality.

This script demonstrates:
1. Creating sample configuration files
2. Loading QueryResources dynamically from YAML/JSON files
3. Using the generated QueryResources with a QueryManager
"""

import asyncio
import tempfile
from pathlib import Path

from fluvius.query import (
    load_query_resources_from_file,
    load_query_resources_from_directory,
    create_sample_config,
    save_sample_config,
    QueryManager
)
from fluvius.query.loader import load_config_file
from pydantic import ValidationError


class DemoQueryManager(QueryManager):
    """Demo query manager for testing loaded resources"""
    
    __abstract__ = True  # Mark as abstract to avoid data manager requirement
    
    def __init__(self):
        # Initialize without calling super() to avoid data manager requirement
        self.__resources__ = {}
        self.__endpoints__ = {}
        
    async def execute_query(self, query_resource, backend_query, meta=None, auth_ctx=None):
        """Mock implementation for demo purposes"""
        return [], {"total": 0, "page": 1}


def demo_create_sample_config():
    """Demo: Create and save sample configuration files"""
    print("=== Demo: Creating Sample Configuration Files ===")
    
    # Create temporary directory for demo files
    temp_dir = Path(tempfile.mkdtemp())
    print(f"Working in temporary directory: {temp_dir}")
    
    # Save sample config as YAML
    yaml_file = temp_dir / "sample_resources.yml"
    save_sample_config(yaml_file, format='yaml')
    print(f"Created YAML config: {yaml_file}")
    
    # Save sample config as JSON
    json_file = temp_dir / "sample_resources.json"
    save_sample_config(json_file, format='json')
    print(f"Created JSON config: {json_file}")
    
    return temp_dir


def demo_load_from_file():
    """Demo: Load QueryResources from a single file"""
    print("\n=== Demo: Loading from Single File ===")
    
    # Create a custom configuration
    config_data = {
        "resources": {
            "blog-posts": {
                "name": "Blog Posts",
                "description": "Query blog posts and articles",
                "backend_model": "posts",
                "tags": ["blog", "content"],
                "fields": {
                    "post_id": {
                        "type": "uuid",
                        "label": "Post ID",
                        "identifier": True
                    },
                    "title": {
                        "type": "string",
                        "label": "Post Title"
                    },
                    "author": {
                        "type": "string",
                        "label": "Author Name"
                    },
                    "published_date": {
                        "type": "datetime",
                        "label": "Published Date"
                    },
                    "status": {
                        "type": "enum",
                        "label": "Publication Status"
                    },
                    "view_count": {
                        "type": "integer",
                        "label": "View Count"
                    },
                    "tags": {
                        "type": "array",
                        "label": "Tags"
                    }
                },
                "meta": {
                    "allow_item_view": True,
                    "allow_list_view": True,
                    "select_all": False,
                    "default_order": ["published_date.desc"]
                }
            },
            "user-comments": {
                "name": "User Comments",
                "description": "Query user comments on posts",
                "backend_model": "comments",
                "fields": {
                    "comment_id": {
                        "type": "uuid",
                        "label": "Comment ID",
                        "identifier": True
                    },
                    "post_id": {
                        "type": "uuid",
                        "label": "Post ID"
                    },
                    "user_name": {
                        "type": "string",
                        "label": "Commenter Name"
                    },
                    "content": {
                        "type": "textsearch",
                        "label": "Comment Content"
                    },
                    "created_at": {
                        "type": "datetime",
                        "label": "Comment Date"
                    },
                    "approved": {
                        "type": "boolean",
                        "label": "Approved"
                    }
                }
            }
        }
    }
    
    # Save to temporary file
    import yaml
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False)
    yaml.dump(config_data, temp_file)
    temp_file.close()
    
    try:
        # Load all resources from the file
        print(f"Loading resources from: {temp_file.name}")
        for resource_id, resource_class in load_query_resources_from_file(temp_file.name):
            print(f"  Loaded resource: {resource_id}")
            print(f"    Class: {resource_class.__name__}")
            print(f"    Meta.name: {resource_class.Meta.name}")
            print(f"    Meta.desc: {resource_class.Meta.desc}")
            
            # Create an instance to inspect fields
            instance = resource_class()
            field_names = [f._key for f in instance.query_fields]
            print(f"    Fields: {field_names}")
            print()
        
        # Load specific resources only
        print("Loading only 'blog-posts' resource:")
        for resource_id, resource_class in load_query_resources_from_file(
            temp_file.name, 
            resource_keys=["blog-posts"]
        ):
            print(f"  Loaded: {resource_id}")
            instance = resource_class()
            print(f"  Default order: {instance.default_order}")
            print()
            
    finally:
        Path(temp_file.name).unlink()


def demo_load_from_directory():
    """Demo: Load QueryResources from a directory"""
    print("\n=== Demo: Loading from Directory ===")
    
    temp_dir = demo_create_sample_config()
    
    try:
        # Load all YAML files from directory
        print(f"Loading all YAML files from: {temp_dir}")
        for file_path, resource_id, resource_class in load_query_resources_from_directory(
            temp_dir, 
            pattern="*.yml"
        ):
            print(f"  File: {Path(file_path).name}")
            print(f"  Resource: {resource_id}")
            print(f"  Name: {resource_class.Meta.name}")
            print()
            
    finally:
        # Cleanup
        for file in temp_dir.iterdir():
            file.unlink()
        temp_dir.rmdir()


def demo_pydantic_validation():
    """Demo: Pydantic validation benefits"""
    print("\n=== Demo: Pydantic Validation ===")
    
    # Example 1: Valid configuration
    print("1. Valid configuration:")
    valid_config = {
        "user-profile": {
            "name": "User Profile",
            "fields": {
                "_id": {"type": "uuid", "identifier": True},
                "username": {"type": "string"}
            }
        }
    }
    
    import yaml
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False)
    yaml.dump(valid_config, temp_file)
    temp_file.close()
    
    try:
        config = load_config_file(temp_file.name)
        print(f"   ✓ Successfully loaded and validated config")
        print(f"   ✓ Found resources: {list(config.get_resources().keys())}")
    except Exception as e:
        print(f"   ✗ Unexpected error: {e}")
    finally:
        Path(temp_file.name).unlink()
    
    # Example 2: Invalid - missing identifier field
    print("\n2. Invalid configuration (missing identifier):")
    invalid_config = {
        "bad-resource": {
            "name": "Bad Resource",
            "fields": {
                "username": {"type": "string", "identifier": False}
            }
        }
    }
    
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False)
    yaml.dump(invalid_config, temp_file)
    temp_file.close()
    
    try:
        config = load_config_file(temp_file.name)
        print(f"   ✗ Unexpectedly succeeded - this should have failed!")
    except ValueError as e:
        print(f"   ✓ Correctly caught validation error: {str(e)[:100]}...")
    finally:
        Path(temp_file.name).unlink()
    
    # Example 3: Invalid field type
    print("\n3. Invalid configuration (bad field type):")
    invalid_config2 = {
        "bad-resource": {
            "name": "Bad Resource", 
            "fields": {
                "_id": {"type": "invalid_type", "identifier": True}
            }
        }
    }
    
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False)
    yaml.dump(invalid_config2, temp_file)
    temp_file.close()
    
    try:
        config = load_config_file(temp_file.name)
        print(f"   ✗ Unexpectedly succeeded - this should have failed!")
    except ValueError as e:
        print(f"   ✓ Correctly caught validation error: {str(e)[:100]}...")
    finally:
        Path(temp_file.name).unlink()
    
    print("   → Pydantic provides type safety and validation at load time!")


def demo_integration_with_query_manager():
    """Demo: Integration with QueryManager"""
    print("\n=== Demo: Integration with QueryManager ===")
    
    # Create a query manager
    query_manager = DemoQueryManager()
    
    # Create a simple config
    config_data = {
        "demo-resource": {
            "name": "Demo Resource",
            "description": "A demonstration resource",
            "fields": {
                "_id": {
                    "type": "uuid",
                    "identifier": True
                },
                "name": {
                    "type": "string",
                    "label": "Name"
                }
            }
        }
    }
    
    import yaml
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False)
    yaml.dump(config_data, temp_file)
    temp_file.close()
    
    try:
        # Load and register the resource
        for resource_id, resource_class in load_query_resources_from_file(temp_file.name):
            print(f"Registering resource: {resource_id}")
            
            # Simulate registration (in real usage, you'd use the query manager's register method)
            query_manager.__resources__ = query_manager.__resources__ or {}
            query_manager.__resources__[resource_id] = resource_class()
            
            print(f"Resource registered with ID: {resource_id}")
            print(f"Resource specs: {query_manager.__resources__[resource_id].specs()}")
            
    finally:
        Path(temp_file.name).unlink()


def demo_custom_field_types():
    """Demo: Using different field types"""
    print("\n=== Demo: Custom Field Types ===")
    
    config_data = {
        "field-demo": {
            "name": "Field Types Demo",
            "description": "Demonstrates different field types",
            "fields": {
                "id": {"type": "uuid", "identifier": True},
                "name": {"type": "string", "label": "Name"},
                "age": {"type": "integer", "label": "Age"},
                "birth_date": {"type": "date", "label": "Birth Date"},
                "created_at": {"type": "datetime", "label": "Created At"},
                "salary": {"type": "float", "label": "Salary"},
                "active": {"type": "boolean", "label": "Active"},
                "skills": {"type": "array", "label": "Skills"},
                "role": {"type": "enum", "label": "Role"},
                "description": {"type": "textsearch", "label": "Description"}
            }
        }
    }
    
    import yaml
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False)
    yaml.dump(config_data, temp_file)
    temp_file.close()
    
    try:
        for resource_id, resource_class in load_query_resources_from_file(temp_file.name):
            print(f"Resource: {resource_id}")
            instance = resource_class()
            
            for field in instance.query_fields:
                field_type = type(field).__name__
                print(f"  {field._key}: {field_type} ('{field.label}')")
                
    finally:
        Path(temp_file.name).unlink()


async def main():
    """Run all demos"""
    print("QueryResource Loader Demo")
    print("=" * 50)
    
    demo_create_sample_config()
    demo_load_from_file()
    demo_load_from_directory()
    demo_pydantic_validation()
    demo_integration_with_query_manager()
    demo_custom_field_types()
    
    print("\n=== Demo Complete ===")
    print("Check the fluvius.query.loader module for more functionality!")


if __name__ == "__main__":
    asyncio.run(main()) 