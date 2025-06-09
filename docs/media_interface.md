# Fluvius Media Interface

The Fluvius Media Interface provides a unified way to store files using fsspec filesystems while tracking metadata through MediaEntry objects. It supports multiple filesystem backends (local, S3, GCS, etc.) and includes features like compression, file deduplication, and resource organization.

## Key Features

- **Multiple Filesystem Support**: Uses fsspec for abstracting different storage backends
- **Metadata Tracking**: Automatic SHA-256 hashing, MIME type detection, file size tracking
- **Compression**: Support for GZIP, BZ2, and LZMA compression
- **Resource Organization**: Associate files with resources and resource IDs
- **Database Integration**: Uses Fluvius DataAccessManager for metadata persistence
- **Testing Support**: Includes NullMediaManager for testing without database

## Architecture

The MediaInterface follows Fluvius patterns and integrates with the DataAccessManager system:

- **MediaEntry**: SQLAlchemy model for file metadata (filename, hash, MIME type, size, etc.)
- **MediaFilesystem**: SQLAlchemy model for filesystem configurations  
- **MediaManager**: Extends DataAccessManager for database operations
- **NullMediaManager**: Implements Null Object Pattern for testing scenarios

## DataAccessManager Integration

The MediaInterface correctly uses the DataAccessManager interface with these key methods:

- **`create(model_name, data)`**: Creates in-memory model instance (NOT async)
- **`insert(record)`**: Saves record to database (async)
- **`fetch(model_name, identifier)`**: Retrieves single record by ID
- **`query(model_name, **params)`**: Query with filtering and pagination
- **`remove(record)`**: Deletes record from database

### Correct Pattern for Creating Records

```python
# Create in-memory instance
entry = manager.create('MediaEntry', entry_data)

# Save to database  
await manager.insert(entry)
```

### Querying Records

```python
# Query with filtering and pagination
entries = await manager.query('MediaEntry', 
                             resource='documents',
                             limit=50, 
                             offset=0)
```

## Null Object Pattern

The MediaInterface uses the Null Object Pattern to eliminate conditional logic. Instead of checking `if self._manager:` throughout the code, it always uses a manager - either a real `MediaManager` or a `NullMediaManager`.

### Benefits:

- **Consistent Code Paths**: Same method calls work in production and testing
- **Eliminated Conditionals**: No scattered `if manager:` checks
- **Simplified Testing**: Tests can run without database setup
- **Better Maintainability**: Single code path reduces complexity

### Implementation:

```python
class MediaInterface:
    def __init__(self, app=None, media_manager=MediaManager):
        if app is not None:
            self._manager = media_manager(app)  # Real manager
        else:
            self._manager = NullMediaManager(app)  # Mock manager
        
    async def put(self, fileobj, **kwargs):
        # Always use manager - no conditionals needed
        entry = self._manager.create('MediaEntry', entry_data)
        await self._manager.insert(entry)
        return entry
```

## Usage Examples

### Basic File Storage

```python
from fluvius.media import MediaInterface

# Initialize (uses NullMediaManager if no app provided)
media = MediaInterface()

# Store a file from bytes
entry = await media.put(
    b"Hello, World!",
    filename="hello.txt",
    resource="documents",
    resource_id="doc_123"
)

print(f"Stored file {entry.filename} with ID {entry._id}")
```

### File Operations

```python
# Open file for reading
with await media.open(entry._id) as f:
    content = f.read()

# Get file content as bytes
content = await media.get(entry._id)

# Check if file exists
exists = await media.exists(entry._id)

# Copy file to another location
copied_entry = await media.copy(entry._id, dest_fs_key='backup')

# Delete file
success = await media.delete(entry._id)
```

### File Compression

```python
from fluvius.media import FsSpecCompressionMethod

# Store file with compression
entry = await media.put(
    large_data,
    filename="large_file.txt",
    compress=FsSpecCompressionMethod.GZIP
)

# Compression is handled transparently when opening
with await media.open(entry._id) as f:
    decompressed_content = f.read()
```

### Filesystem Registration

```python
# Register S3 filesystem
await media.register_filesystem(
    'my_s3',
    's3', 
    'My S3 Bucket',
    bucket='my-bucket',
    key='access-key',
    secret='secret-key'
)

# Store file to specific filesystem
entry = await media.put(
    file_data,
    filename="cloud_file.txt",
    fs_key='my_s3'
)
```

### Listing Files

```python
# List all files
all_files = await media.list_files()

# List files by resource
doc_files = await media.list_files(resource='documents')

# List with pagination
page_files = await media.list_files(limit=20, offset=40)

# List by resource and resource_id
specific_files = await media.list_files(
    resource='documents',
    resource_id='doc_123'
)
```

## Production Configuration

When using with a Fluvius app, provide the app instance:

```python
from fluvius.media import MediaInterface, MediaManager

# Production usage with database
app = FluviusApp()
media = MediaInterface(app=app, media_manager=MediaManager)

# Filesystem cache for performance
filesystem_cache = {}
media = MediaInterface(app=app, filesystem_cache=filesystem_cache)
```

## Testing

The MediaInterface can be used in tests without database setup:

```python
import pytest
from fluvius.media import MediaInterface

@pytest.fixture
def media_interface():
    # Uses NullMediaManager automatically
    return MediaInterface()

@pytest.mark.asyncio
async def test_file_storage(media_interface):
    # Works without database
    entry = await media_interface.put(b"test data", filename="test.txt")
    content = await media_interface.get(entry._id)
    assert content == b"test data"
```

## API Reference

### MediaInterface

#### Methods

- **`put(fileobj, filename=None, fs_key=None, compress=None, resource=None, resource_id=None, **metadata_kwargs)`**
  - Store a file and create metadata entry
  - Returns: MediaEntry

- **`open(file_id, mode='rb')`**
  - Open a file by MediaEntry ID
  - Returns: File-like object

- **`get(file_id)`**
  - Get file content as bytes
  - Returns: bytes

- **`delete(file_id)`**
  - Delete file and metadata
  - Returns: bool

- **`exists(file_id)`**
  - Check if file exists
  - Returns: bool

- **`copy(file_id, dest_fs_key=None)`**
  - Copy file to another location
  - Returns: MediaEntry

- **`list_files(resource=None, resource_id=None, limit=100, offset=0)`**
  - List files with filtering
  - Returns: List[MediaEntry]

- **`register_filesystem(fs_key, protocol, name, **params)`**
  - Register filesystem configuration
  - Returns: MediaFilesystem

- **`get_filesystem(fs_key)`**
  - Get filesystem instance
  - Returns: fsspec.AbstractFileSystem

- **`get_metadata(file_id)`**
  - Get file metadata
  - Returns: MediaEntry

### NullMediaManager

Mock implementation of MediaManager interface for testing:

#### Methods

- **`create(model_name, data=None, **kwargs)`**
  - Create mock model instance (not async)
  - Returns: Mock object

- **`insert(record)`**
  - Mock insert operation (async)
  - Returns: record

- **`fetch(model_name, identifier)`**
  - Mock fetch operation
  - Returns: Mock object

- **`remove(record)`**
  - Mock remove operation
  - Returns: bool

- **`query(model_name, q=None, return_meta=None, **query_params)`**
  - Mock query with filtering and pagination
  - Returns: List of mock objects

## Configuration

Configuration is handled through `fluvius.media._meta.config`:

```python
# Default settings
DEFAULT_FILESYSTEM = 'file'
DATABASE_DSN = 'sqlite:///media.db'
SCHEMA_NAME = 'media'
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
CHUNK_SIZE = 64 * 1024  # 64KB
```

## Error Handling

The MediaInterface raises appropriate exceptions:

- **`ValueError`**: Invalid parameters or missing files
- **`FileNotFoundError`**: File not found in filesystem
- **`PermissionError`**: Insufficient permissions
- **Database exceptions**: Propagated from DataAccessManager

Example error handling:

```python
try:
    entry = await media.put(file_data, filename="test.txt")
    content = await media.get(entry._id)
except ValueError as e:
    logger.error(f"Invalid input: {e}")
except FileNotFoundError as e:
    logger.error(f"File not found: {e}")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
``` 