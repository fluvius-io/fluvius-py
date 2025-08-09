import io
import os
import uuid
import mimetypes
import fsspec
from pathlib import Path
from typing import Union, BinaryIO, Optional, Dict, Any
from datetime import datetime, timezone
from fluvius.helper import load_yaml

from ._meta import config, logger
from .model import MediaManager, MediaEntry, MediaFilesystem, FsSpecCompressionMethod
from .helper import gen_token, hash_n_length
from .nullmgr import NullMediaManager
from .compressor import MediaCompressor


class MediaInterface:
    """Interface for storing files with fsspec.filesystem and tracking metadata with MediaEntry objects"""
    
    def __init__(self, app=None, media_manager=MediaManager, filesystem_cache: Optional[Dict[str, fsspec.AbstractFileSystem]] = None):
        self._app = app
        
        # Always ensure we have a manager - use NullMediaManager for testing if no app provided
        self._manager = media_manager(app) if app is not None else NullMediaManager(app)
        self._filesystem_cache = filesystem_cache or {}
        self._default_fs_key = config.DEFAULT_FILESYSTEM
        self._REGISTRY = {}
        self.register_filesystem()

    async def put(
        self, 
        fileobj: Union[BinaryIO, bytes, str, Path], 
        filename: Optional[str] = None,
        fs_key: Optional[str] = None,
        compress: Optional[FsSpecCompressionMethod] = None,
        resource: Optional[str] = None,
        resource_id: Optional[str] = None,
        mime_type: Optional[str] = None,
        **metadata_kwargs
    ) -> MediaEntry:
        """
        Store a file in the filesystem and create a MediaEntry record.
        
        Args:
            fileobj: File object, bytes, file path, or pathlib.Path
            filename: Original filename (auto-detected if fileobj is a path)
            fs_key: Filesystem key to use (defaults to DEFAULT_FILESYSTEM)
            compress: Compression method to use
            resource: Resource type this file belongs to
            resource_id: ID of the resource this file belongs to
            **metadata_kwargs: Additional metadata fields
            
        Returns:
            MediaEntry: Created media entry with metadata
        """
        fs_key = fs_key or self._default_fs_key

        # Get filesystem and store file
        fs = await self.get_filesystem(fs_key)
        fs_spec = self._REGISTRY[fs_key]
        
        # Prepare file data
        if isinstance(fileobj, (str, Path)):
            filepath = Path(fileobj)
            filename = filename or filepath.name
            with open(filepath, 'rb') as f:
                file_data = f.read()
        elif isinstance(fileobj, bytes):
            file_data = fileobj
        else:
            # Assume it's a file-like object
            file_data = fileobj.read()
            if hasattr(fileobj, 'seek'):
                fileobj.seek(0)  # Reset position
        
        if not filename and hasattr(fileobj, 'name'):
            filename = getattr(fileobj, 'name', 'unnamed_file')
        
        # Generate file hash and get length
        file_io = io.BytesIO(file_data)
        filehash, length = hash_n_length(file_io)

        # Generate unique file path
        file_token = gen_token()
        file_ext = Path(filename).suffix if filename else ''
        fspath = f"{fs_spec.root_path}/{file_token}{file_ext}"

        # Detect MIME type
        filemime = mime_type or mimetypes.guess_type(filename)[0] or 'application/octet-stream'

        # Apply compression if specified
        file_to_store = file_data
        if compress:
            file_to_store = MediaCompressor.get(compress).compress(file_data)
            
        # Store file
        with fs.open(fspath, 'wb') as f:
            f.write(file_to_store)
            
        logger.info(f"Stored file {filename} ({length} bytes) at {fspath} in filesystem {fs_key}")
        
        # Create MediaEntry record using correct DataAccessManager pattern
        entry_data = {
            '_id': uuid.uuid4(),
            'filename': filename or 'unnamed_file',
            'filehash': filehash,
            'filemime': filemime,
            'fskey': fs_key,
            'length': length,
            'fspath': fspath,
            'compress': compress,
            'resource': resource,
            'resource__id': resource_id,
            **metadata_kwargs
        }
        async with self._manager.transaction():
            # Create in-memory model then insert to database
            entry = self._manager.create('media-entry', entry_data)
            await self._manager.insert(entry)
        return entry

    async def open(self, file_id: str, mode: str = 'rb') -> BinaryIO:
        """
        Open a file by its MediaEntry ID.
        
        Args:
            file_id: MediaEntry ID
            mode: File mode (default: 'rb')
            
        Returns:
            File-like object
        """
        metadata = await self.get_metadata(file_id)
        fs = await self.get_filesystem(metadata.fskey)
        
        file_handle = fs.open(metadata.fspath, mode)
        
        # Handle decompression if needed
        if metadata.compress:
            compressor = MediaCompressor.get(metadata.compress)
            # Read compressed data and return decompressed file handle
            compressed_data = file_handle.read()
            file_handle.close()
            file_handle = compressor.open_compressed(compressed_data)
            
        logger.info(f"Opened file {metadata.filename} from {metadata.fspath}")
        return file_handle

    async def stream(self, file_id: str):
        def _stream_file(fs, fspath):
            with fs.open(fspath, "rb") as f:
                while chunk := f.read(config.CHUNK_SIZE):
                    yield chunk

        """
        Stream a file by its MediaEntry ID.
        """
        metadata = await self.get_metadata(file_id)
        fs = await self.get_filesystem(metadata.fskey)

        return _stream_file(fs, metadata.fspath)

    async def get(self, file_id: str) -> bytes:
        """
        Get file content as bytes by MediaEntry ID.
        
        Args:
            file_id: MediaEntry ID
            
        Returns:
            File content as bytes
        """
        with await self.open(file_id, 'rb') as f:
            return f.read()

    async def delete(self, file_id: str) -> bool:
        """
        Delete a file and its metadata.
        
        Args:
            file_id: MediaEntry ID
            
        Returns:
            True if successful
        """
        metadata = await self.get_metadata(file_id)
        fs = await self.get_filesystem(metadata.fskey)
        
        try:
            # Delete file from filesystem
            fs.rm(metadata.fspath)
            logger.info(f"Deleted file {metadata.filename} from {metadata.fspath}")
            
            # Delete metadata record using manager
            await self._manager.remove(metadata)
                
            return True
        except Exception as e:
            logger.error(f"Failed to delete file {file_id}: {e}")
            raise

    async def exists(self, file_id: str) -> bool:
        """
        Check if a file exists.
        
        Args:
            file_id: MediaEntry ID
            
        Returns:
            True if file exists
        """
        try:
            metadata = await self.get_metadata(file_id)
            fs = await self.get_filesystem(metadata.fskey)
            return fs.exists(metadata.fspath)
        except Exception:
            return False

    async def copy(self, file_id: str, dest_fs_key: Optional[str] = None) -> MediaEntry:
        """
        Copy a file to another filesystem or location.
        
        Args:
            file_id: Source MediaEntry ID
            dest_fs_key: Destination filesystem key
            
        Returns:
            New MediaEntry for the copied file
        """
        source_metadata = await self.get_metadata(file_id)
        dest_fs_key = dest_fs_key or source_metadata.fskey
        
        # Get file content
        file_data = await self.get(file_id)
        
        # Create new entry with copied data
        return await self.put(
            file_data,
            filename=f"copy_of_{source_metadata.filename}",
            fs_key=dest_fs_key,
            compress=source_metadata.compress,
            resource=source_metadata.resource,
            resource_id=source_metadata.resource__id
        )

    async def get_filesystem(self, fs_key: str) -> fsspec.AbstractFileSystem:
        """
        Get or create a filesystem instance.
        
        Args:
            fs_key: Filesystem identifier
            
        Returns:
            fsspec filesystem instance
        """
        if fs_key in self._filesystem_cache:
            return self._filesystem_cache[fs_key]

        # Try to fetch filesystem configuration from manager. Let errors propagate.
        fs_spec = self._REGISTRY.get(fs_key)
        if not fs_spec:
            raise ValueError(f"Filesystem {fs_key} not found")

        fsys = fsspec.filesystem(fs_spec.protocol, **fs_spec.params)

        self._filesystem_cache[fs_key] = fsys

        return fsys

    async def get_metadata(self, file_id: str) -> MediaEntry:
        """
        Get MediaEntry metadata by ID.
        
        Args:
            file_id: MediaEntry ID
            
        Returns:
            MediaEntry instance
        """
        # Always use manager (either real or null)
        async with self._manager.transaction():
            return await self._manager.fetch('media-entry', file_id)

    async def list_files(
        self, 
        resource: Optional[str] = None,
        resource_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> list[MediaEntry]:
        """
        List files with optional filtering.
        
        Args:
            resource: Filter by resource type
            resource_id: Filter by resource ID
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of MediaEntry instances
        """
        query_params = {'limit': limit, 'offset': offset}
        if resource:
            query_params['resource'] = resource
        if resource_id:
            query_params['resource__id'] = resource_id
            
        # Use the correct DataAccessManager method
        async with self._manager.transaction():
            return await self._manager.query('media-entry', **query_params)

    def register_filesystem(self):
        """Load filesystem configurations from YAML file and register them"""
        try:
            fs_configs = load_yaml(config.FILESYSTEM_CONFIG_PATH)
            logger.info(f"Loaded filesystem configs: {fs_configs}")
            for fs_spec in fs_configs['filesystems']:
                self._REGISTRY[fs_spec['fskey']] = MediaFilesystem(**fs_spec)
                logger.info(f"Registered filesystem {fs_spec['fskey']}")
                
        except Exception as e:
            logger.error(f"Failed to load filesystem configs: {e}")
            raise
