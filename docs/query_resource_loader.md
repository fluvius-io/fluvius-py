# QueryResource Dynamic Loader

The `fluvius.query.loader` module provides functionality to dynamically create `QueryResource` classes from YAML or JSON configuration files. This allows you to define query resources declaratively without writing Python code for each resource.

## Features

- **Multi-format support**: Load from YAML (`.yml`, `.yaml`) or JSON (`.json`) files
- **Dynamic field creation**: Support for all built-in field types (string, integer, date, etc.)
- **Flexible configuration**: Configure resource metadata, field properties, and validation
- **Generator-based loading**: Memory-efficient loading with generator functions
- **Directory scanning**: Load multiple resources from directories
- **Sample configurations**: Built-in sample configurations for quick start

## Quick Start

### 1. Create a Configuration File

Create a YAML file (`resources.yml`) with your QueryResource definitions:

```yaml
resources:
  user-profile:
    name: "User Profile"
    description: "Query user profile information"
    backend_model: "user_profile"
    tags: ["user", "profile"]
    fields:
      _id:
        type: "uuid"
        label: "User ID"
        identifier: true
      username:
        type: "string"
        label: "Username"
        sortable: true
      email:
        type: "string"
        label: "Email Address"
      created_at:
        type: "datetime"
        label: "Created Date"
        sortable: true
      status:
        type: "enum"
        label: "Account Status"
    meta:
      allow_item_view: true
      allow_list_view: true
      select_all: false
```

### 2. Load QueryResources

```python
from fluvius.query import load_query_resources_from_file

# Load all resources from file
for resource_id, resource_class in load_query_resources_from_file('resources.yml'):
    print(f"Loaded: {resource_id}")
    # Register with your query manager
    query_manager.register_resource_class(resource_id, resource_class)
```

### 3. Use with QueryManager

```python
from fluvius.query import QueryManager

class MyQueryManager(QueryManager):
    # ... your implementation

# Create query manager instance
query_manager = MyQueryManager()

# Load and register resources
for resource_id, resource_class in load_query_resources_from_file('resources.yml'):
    # Use the decorator pattern or direct registration
    decorated_class = query_manager.register_resource(resource_id)(resource_class)
```

## Configuration Format

### Resource Structure

```yaml
resources:
  resource-id:
    name: "Human Readable Name"           # Required
    description: "Resource description"    # Optional
    backend_model: "database_table"       # Optional
    tags: ["tag1", "tag2"]                # Optional
    fields: { ... }                       # Required
    meta: { ... }                         # Optional
```

### Field Configuration

```yaml
fields:
  field_name:
    type: "string"          # Field type (see supported types below)
    label: "Display Name"   # Human-readable label
    sortable: true          # Whether field is sortable (default: true)
    hidden: false           # Whether field is hidden (default: false)
    identifier: false       # Whether this is the identifier field (default: false)
    source: "db_column"     # Source column name (default: field_name)
```

### Supported Field Types

| Type | QueryField Class | Description |
|------|------------------|-------------|
| `string`, `text` | `StringField` | Text fields with string operations |
| `integer`, `int` | `IntegerField` | Numeric fields with range operations |
| `date` | `DateField` | Date fields |
| `datetime`, `timestamp` | `DateTimeField` | Date-time fields |
| `float`, `decimal` | `FloatField` | Floating-point numeric fields |
| `boolean`, `bool` | `BooleanField` | Boolean fields |
| `enum` | `EnumField` | Enumeration fields |
| `uuid` | `UUIDField` | UUID fields |
| `array`, `list` | `ArrayField` | Array/list fields |
| `textsearch`, `fulltext` | `TextSearchField` | Full-text search fields |

### Meta Configuration

```yaml
meta:
  allow_item_view: true       # Allow single item queries
  allow_list_view: true       # Allow list queries
  allow_meta_view: true       # Allow metadata queries
  auth_required: true         # Require authentication
  select_all: false           # Select all fields by default
  default_order: ["field.asc", "other.desc"]  # Default sort order
```

## API Reference

### Loading Functions

#### `load_query_resources_from_file(file_path, resource_keys=None)`

Load QueryResources from a single file.

**Parameters:**
- `file_path` (str|Path): Path to YAML or JSON configuration file
- `resource_keys` (List[str], optional): Specific resource keys to load

**Yields:**
- `Tuple[str, type]`: (resource_identifier, QueryResource_class)

**Example:**
```python
# Load all resources
for resource_id, resource_class in load_query_resources_from_file('config.yml'):
    print(f"Loaded: {resource_id}")

# Load specific resources only
for resource_id, resource_class in load_query_resources_from_file(
    'config.yml', 
    resource_keys=['user-profile', 'orders']
):
    print(f"Loaded: {resource_id}")
```

#### `load_query_resources_from_directory(directory_path, pattern="*.yml", recursive=False)`

Load QueryResources from all matching files in a directory.

**Parameters:**
- `directory_path` (str|Path): Directory containing configuration files
- `pattern` (str): File pattern to match (default: "*.yml")
- `recursive` (bool): Search subdirectories recursively

**Yields:**
- `Tuple[str, str, type]`: (file_path, resource_identifier, QueryResource_class)

**Example:**
```python
# Load from directory
for file_path, resource_id, resource_class in load_query_resources_from_directory('./configs'):
    print(f"From {file_path}: {resource_id}")

# Load JSON files recursively
for file_path, resource_id, resource_class in load_query_resources_from_directory(
    './configs', 
    pattern='*.json', 
    recursive=True
):
    print(f"From {file_path}: {resource_id}")
```

### Utility Functions

#### `create_sample_config()`

Create a sample configuration dictionary.

**Returns:**
- `Dict[str, Any]`: Sample configuration

#### `save_sample_config(file_path, format='yaml')`

Save a sample configuration to a file.

**Parameters:**
- `file_path` (str|Path): Output file path
- `format` (str): Output format ('yaml' or 'json')

**Example:**
```python
from fluvius.query import save_sample_config

# Create sample YAML config
save_sample_config('sample_resources.yml', format='yaml')

# Create sample JSON config
save_sample_config('sample_resources.json', format='json')
```

## Advanced Usage

### Custom Field Configuration

```yaml
fields:
  price:
    type: "float"
    label: "Product Price"
    sortable: true
    # Custom field properties can be added
    
  search_content:
    type: "textsearch"
    label: "Search Content"
    hidden: true  # Hidden from default selection
    
  category_id:
    type: "uuid"
    label: "Category"
    source: "category_fk"  # Maps to different database column
```

### Multiple Resource Files

```python
import glob
from fluvius.query import load_query_resources_from_file

# Load from multiple files
config_files = glob.glob('configs/*.yml')
for config_file in config_files:
    for resource_id, resource_class in load_query_resources_from_file(config_file):
        query_manager.register_resource(resource_id)(resource_class)
```

### Environment-Specific Configurations

```python
import os
from fluvius.query import load_query_resources_from_file

# Load environment-specific config
env = os.getenv('ENVIRONMENT', 'development')
config_file = f'configs/resources_{env}.yml'

for resource_id, resource_class in load_query_resources_from_file(config_file):
    query_manager.register_resource(resource_id)(resource_class)
```

## Error Handling

The loader functions provide clear error messages for common issues:

- **File not found**: `FileNotFoundError` with file path
- **Invalid format**: `ValueError` for unsupported file extensions
- **Parse errors**: `ValueError` for YAML/JSON syntax errors  
- **Invalid field types**: `ValueError` for unsupported field types
- **Missing resources**: `ValueError` when requested resource keys don't exist

```python
try:
    for resource_id, resource_class in load_query_resources_from_file('config.yml'):
        # Process resource
        pass
except FileNotFoundError as e:
    print(f"Configuration file not found: {e}")
except ValueError as e:
    print(f"Configuration error: {e}")
```

## Best Practices

1. **Organize by domain**: Group related resources in separate files
2. **Use descriptive names**: Make resource IDs and field names self-documenting
3. **Validate configurations**: Test load configurations in development
4. **Version control**: Keep configuration files in version control
5. **Environment separation**: Use different configs for dev/staging/prod
6. **Documentation**: Document custom field types and business rules

## Example: Complete Workflow

```python
from fluvius.query import (
    load_query_resources_from_directory,
    QueryManager
)

class ProductQueryManager(QueryManager):
    # Your query manager implementation
    pass

# Initialize query manager
query_manager = ProductQueryManager()

# Load all resource configurations
resource_count = 0
for file_path, resource_id, resource_class in load_query_resources_from_directory(
    'configs/resources/',
    pattern='*.yml'
):
    # Register resource with manager
    decorated_class = query_manager.register_resource(resource_id)(resource_class)
    resource_count += 1
    print(f"Registered {resource_id} from {file_path}")

print(f"Loaded {resource_count} QueryResources successfully!")

# Resources are now available for querying
# query_manager.query_resource('user-profile', frontend_query)
```

This dynamic loading approach makes it easy to maintain QueryResources as configuration rather than code, enabling faster development and easier maintenance of query interfaces. 