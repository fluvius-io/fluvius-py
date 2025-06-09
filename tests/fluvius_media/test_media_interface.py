import pytest
import asyncio
import tempfile
import io
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from fluvius.media import MediaInterface, MediaEntry, FsSpecCompressionMethod, NullMediaManager


class TestNullMediaManager:
    """Test suite for NullMediaManager functionality"""
    
    @pytest.fixture
    def null_manager(self):
        """Create a NullMediaManager instance"""
        return NullMediaManager()
    
    @pytest.mark.asyncio
    async def test_create_and_insert_media_entry(self, null_manager):
        """Test creating and inserting a MediaEntry with NullMediaManager"""
        entry_data = {
            'filename': 'test.txt',
            'filehash': 'abcd1234',
            'filemime': 'text/plain',
            'fskey': 'file',
            'length': 100,
            'fspath': 'test.txt'
        }
        
        # Create in-memory entry (not async)
        entry = null_manager.create('MediaEntry', entry_data)
        
        assert entry.filename == 'test.txt'
        assert entry.filehash == 'abcd1234'
        assert entry.filemime == 'text/plain'
        assert entry._id  # Should have an ID
        
        # Insert to "database" (async)
        inserted_entry = await null_manager.insert(entry)
        
        # Verify it's stored in manager
        assert entry._id in null_manager._entries
        assert inserted_entry == entry
    
    @pytest.mark.asyncio
    async def test_fetch_media_entry(self, null_manager):
        """Test fetching a MediaEntry with NullMediaManager"""
        # Create and insert an entry first
        entry_data = {'filename': 'test.txt', 'length': 100}
        entry = null_manager.create('MediaEntry', entry_data)
        await null_manager.insert(entry)
        
        # Fetch it back
        fetched_entry = await null_manager.fetch('MediaEntry', entry._id)
        
        assert fetched_entry.filename == 'test.txt'
        assert fetched_entry.length == 100
        assert fetched_entry._id == entry._id
    
    @pytest.mark.asyncio
    async def test_fetch_nonexistent_entry(self, null_manager):
        """Test fetching a non-existent entry raises error"""
        with pytest.raises(ValueError, match="MediaEntry.*not found"):
            await null_manager.fetch('MediaEntry', 'nonexistent-id')
    
    @pytest.mark.asyncio
    async def test_remove_media_entry(self, null_manager):
        """Test removing a MediaEntry with NullMediaManager"""
        # Create and insert an entry
        entry = null_manager.create('MediaEntry', {'filename': 'test.txt'})
        await null_manager.insert(entry)
        entry_id = entry._id
        
        # Verify it exists
        assert entry_id in null_manager._entries
        
        # Remove it
        result = await null_manager.remove(entry)
        
        assert result is True
        assert entry_id not in null_manager._entries
    
    @pytest.mark.asyncio
    async def test_query_media_entries(self, null_manager):
        """Test querying MediaEntries with filtering"""
        # Create and insert multiple entries
        entry1 = null_manager.create('MediaEntry', {'filename': 'file1.txt', 'resource': 'docs'})
        entry2 = null_manager.create('MediaEntry', {'filename': 'file2.txt', 'resource': 'images'})
        entry3 = null_manager.create('MediaEntry', {'filename': 'file3.txt', 'resource': 'docs'})
        
        await null_manager.insert(entry1)
        await null_manager.insert(entry2)
        await null_manager.insert(entry3)
        
        # Query all entries
        all_entries = await null_manager.query('MediaEntry')
        assert len(all_entries) == 3
        
        # Query with filter
        doc_entries = await null_manager.query('MediaEntry', resource='docs')
        assert len(doc_entries) == 2
        assert all(entry.resource == 'docs' for entry in doc_entries)
        
        # Query with pagination
        paginated = await null_manager.query('MediaEntry', limit=2, offset=1)
        assert len(paginated) == 2
    
    @pytest.mark.asyncio
    async def test_create_and_insert_filesystem(self, null_manager):
        """Test creating and inserting a MediaFilesystem with NullMediaManager"""
        fs_data = {
            'fskey': 'test-s3',
            'protocol': 's3',
            'name': 'Test S3',
            'params': {'bucket': 'test-bucket'}
        }
        
        # Create and insert filesystem
        filesystem = null_manager.create('MediaFilesystem', fs_data)
        await null_manager.insert(filesystem)
        
        assert filesystem.fskey == 'test-s3'
        assert filesystem.protocol == 's3'
        assert filesystem.name == 'Test S3'
        assert filesystem._id
        
        # Verify it's stored
        assert 'test-s3' in null_manager._filesystems


class TestMediaInterface:
    """Test suite for MediaInterface functionality"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            yield Path(tmp_dir)
    
    @pytest.fixture 
    def media_interface(self):
        """Create a MediaInterface instance for testing (without database)"""
        return MediaInterface()
    
    @pytest.fixture
    def mock_manager(self):
        """Create a mock MediaManager for testing with database"""
        manager = AsyncMock()
        # Mock the create method to return a mock entry
        def mock_create(model_name, data=None, **kwargs):
            all_data = (data or {})
            all_data.update(kwargs)
            mock_entry = MagicMock()
            mock_entry._id = 'mock-id'
            for key, value in all_data.items():
                setattr(mock_entry, key, value)
            return mock_entry
        
        manager.create = MagicMock(side_effect=mock_create)
        manager.insert = AsyncMock()
        manager.fetch = AsyncMock()
        manager.remove = AsyncMock()
        manager.query = AsyncMock()
        return manager
    
    @pytest.fixture
    def media_interface_with_manager(self, mock_manager):
        """Create MediaInterface with mocked manager"""
        interface = MediaInterface()
        interface._manager = mock_manager
        return interface
    
    def test_null_manager_initialization(self):
        """Test that MediaInterface initializes with NullMediaManager when no app provided"""
        interface = MediaInterface()
        assert isinstance(interface._manager, NullMediaManager)
    
    def test_real_manager_initialization(self):
        """Test that MediaInterface uses real manager when app is provided"""
        # Mock app object
        mock_app = MagicMock()
        
        # Create MediaInterface with app
        interface = MediaInterface(app=mock_app)
        
        # Should not be NullMediaManager (would be real MediaManager in production)
        assert not isinstance(interface._manager, NullMediaManager)
    
    @pytest.mark.asyncio
    async def test_put_file_from_bytes(self, media_interface, temp_dir):
        """Test storing a file from bytes"""
        # Prepare test data
        test_content = b"Hello, World! This is test content."
        filename = "test_file.txt"
        
        # Configure filesystem to use temp directory
        media_interface._filesystem_cache['file'] = MockFilesystem(temp_dir)
        
        # Store file
        entry = await media_interface.put(
            test_content,
            filename=filename,
            resource="test",
            resource_id="123"
        )
        
        # Verify entry
        assert entry.filename == filename
        assert entry.length == len(test_content)
        assert entry.filemime == "text/plain"
        assert entry.resource == "test"
        assert entry.resource__id == "123"
        assert entry.filehash  # Should have a hash
        assert entry.fspath  # Should have a path
    
    @pytest.mark.asyncio
    async def test_put_file_from_path(self, media_interface, temp_dir):
        """Test storing a file from a file path"""
        # Create test file
        test_file = temp_dir / "source.txt"
        test_content = b"File content from path"
        test_file.write_bytes(test_content)
        
        # Configure filesystem
        media_interface._filesystem_cache['file'] = MockFilesystem(temp_dir)
        
        # Store file
        entry = await media_interface.put(test_file)
        
        # Verify entry
        assert entry.filename == "source.txt"
        assert entry.length == len(test_content)
        assert entry.filemime == "text/plain"
    
    @pytest.mark.asyncio
    async def test_put_file_with_compression(self, media_interface, temp_dir):
        """Test storing a file with compression"""
        test_content = b"This content will be compressed using gzip."
        
        # Configure filesystem
        media_interface._filesystem_cache['file'] = MockFilesystem(temp_dir)
        
        # Store file with compression
        entry = await media_interface.put(
            test_content,
            filename="compressed.txt",
            compress=FsSpecCompressionMethod.GZIP
        )
        
        # Verify compression was applied
        assert entry.compress == FsSpecCompressionMethod.GZIP
        # The stored file should be compressed (different size)
        stored_size = len(media_interface._filesystem_cache['file'].files[entry.fspath])
        assert stored_size != len(test_content)  # Should be different due to compression
    
    @pytest.mark.asyncio 
    async def test_open_file(self, media_interface, temp_dir):
        """Test opening a stored file"""
        test_content = b"Content to read back"
        
        # Configure filesystem
        media_interface._filesystem_cache['file'] = MockFilesystem(temp_dir)
        
        # Store file first
        entry = await media_interface.put(test_content, filename="readable.txt")
        
        # Open and read file
        file_handle = await media_interface.open(entry._id)
        read_content = file_handle.read()
        
        assert read_content == test_content
    
    @pytest.mark.asyncio
    async def test_get_file_content(self, media_interface, temp_dir):
        """Test getting file content as bytes"""
        test_content = b"Content to retrieve"
        
        # Configure filesystem
        media_interface._filesystem_cache['file'] = MockFilesystem(temp_dir)
        
        # Store file
        entry = await media_interface.put(test_content, filename="retrieve.txt")
        
        # Get content
        retrieved_content = await media_interface.get(entry._id)
        
        assert retrieved_content == test_content
    
    @pytest.mark.asyncio
    async def test_delete_file(self, media_interface, temp_dir):
        """Test deleting a file"""
        test_content = b"Content to delete"
        
        # Configure filesystem
        filesystem = MockFilesystem(temp_dir)
        media_interface._filesystem_cache['file'] = filesystem
        
        # Store file
        entry = await media_interface.put(test_content, filename="deleteme.txt")
        
        # Verify file exists
        assert entry.fspath in filesystem.files
        
        # Delete file
        success = await media_interface.delete(entry._id)
        
        assert success is True
        assert entry.fspath not in filesystem.files
    
    @pytest.mark.asyncio
    async def test_exists_file(self, media_interface, temp_dir):
        """Test checking if a file exists"""
        test_content = b"Existence test"
        
        # Configure filesystem
        media_interface._filesystem_cache['file'] = MockFilesystem(temp_dir)
        
        # Store file
        entry = await media_interface.put(test_content, filename="exists.txt")
        
        # Check existence
        exists = await media_interface.exists(entry._id)
        assert exists is True
    
    @pytest.mark.asyncio
    async def test_copy_file(self, media_interface, temp_dir):
        """Test copying a file"""
        test_content = b"Content to copy"
        
        # Configure filesystem
        media_interface._filesystem_cache['file'] = MockFilesystem(temp_dir)
        
        # Store original file
        original_entry = await media_interface.put(test_content, filename="original.txt")
        
        # Copy file
        copied_entry = await media_interface.copy(original_entry._id)
        
        # Verify copy
        assert copied_entry._id != original_entry._id
        assert copied_entry.filename.startswith("copy_of_")
        assert copied_entry.length == original_entry.length
        
        # Verify content is the same
        original_content = await media_interface.get(original_entry._id)
        copied_content = await media_interface.get(copied_entry._id)
        assert original_content == copied_content
    
    @pytest.mark.asyncio
    async def test_register_filesystem(self, media_interface_with_manager):
        """Test registering a new filesystem configuration"""
        # Setup mock to return a filesystem object
        mock_fs = MagicMock()
        mock_fs.fskey = 'test_s3'
        media_interface_with_manager._manager.create.return_value = mock_fs
        media_interface_with_manager._manager.insert.return_value = mock_fs
        
        # Register filesystem
        result = await media_interface_with_manager.register_filesystem(
            'test_s3',
            's3',
            'Test S3 Bucket',
            bucket='my-bucket',
            key='access-key'
        )
        
        # Verify manager was called correctly
        media_interface_with_manager._manager.create.assert_called_once_with(
            'MediaFilesystem',
            {
                'fskey': 'test_s3',
                'protocol': 's3', 
                'name': 'Test S3 Bucket',
                'params': {'bucket': 'my-bucket', 'key': 'access-key'}
            }
        )
        # Verify insert was called exactly once (with whatever object create returned)
        media_interface_with_manager._manager.insert.assert_called_once()
        
        # Verify the returned object has the expected attribute
        assert result.fskey == 'test_s3'
    
    @pytest.mark.asyncio
    async def test_list_files(self, media_interface_with_manager):
        """Test listing files with filtering"""
        # Setup mock
        mock_entries = [MagicMock(), MagicMock()]
        media_interface_with_manager._manager.query.return_value = mock_entries
        
        # List files
        result = await media_interface_with_manager.list_files(
            resource='documents',
            resource_id='456',
            limit=50
        )
        
        # Verify manager was called with correct parameters
        media_interface_with_manager._manager.query.assert_called_once_with(
            'MediaEntry',
            limit=50,
            offset=0,
            resource='documents',
            resource__id='456'
        )
        assert result == mock_entries
    
    def test_hash_consistency(self):
        """Test that same content produces same hash"""
        from fluvius.media.helper import hash_n_length
        
        content1 = io.BytesIO(b"Test content")
        content2 = io.BytesIO(b"Test content")
        
        hash1, length1 = hash_n_length(content1)
        hash2, length2 = hash_n_length(content2)
        
        assert hash1 == hash2
        assert length1 == length2


class MockFilesystem:
    """Mock filesystem for testing that simulates file operations"""
    
    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.files = {}  # filename -> content mapping
    
    def open(self, path: str, mode: str = 'rb'):
        """Mock file opening"""
        if 'w' in mode:
            return MockWriteFile(self, path)
        else:
            if path not in self.files:
                raise FileNotFoundError(f"File {path} not found")
            return MockReadFile(self.files[path])
    
    def exists(self, path: str) -> bool:
        """Check if file exists"""
        return path in self.files
        
    def rm(self, path: str):
        """Remove file"""
        if path in self.files:
            del self.files[path]


class MockWriteFile:
    """Mock write file handle"""
    
    def __init__(self, filesystem: MockFilesystem, path: str):
        self.filesystem = filesystem
        self.path = path
        self.content = io.BytesIO()
    
    def write(self, data: bytes):
        self.content.write(data)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Store content in filesystem
        self.filesystem.files[self.path] = self.content.getvalue()


class MockReadFile:
    """Mock read file handle"""
    
    def __init__(self, content: bytes):
        self._content = io.BytesIO(content)
    
    def read(self, size: int = -1) -> bytes:
        return self._content.read(size)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass 