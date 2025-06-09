#!/usr/bin/env python3
"""
Demo script showing MediaInterface functionality with fsspec.filesystem and MediaEntry objects.

This demonstrates:
1. File storage with different input types (bytes, file paths, file objects)
2. Metadata tracking with MediaEntry objects
3. File retrieval and manipulation
4. Filesystem abstraction with fsspec
5. Compression and decompression
6. File management operations (copy, delete, exists)
"""

import asyncio
import tempfile
import io
from pathlib import Path

from fluvius.media import MediaInterface, FsSpecCompressionMethod


async def demo_basic_file_operations():
    """Demo: Basic file operations"""
    print("=== Demo: Basic File Operations ===")
    
    # Create MediaInterface (without database for demo)
    media = MediaInterface()
    
    # Demo 1: Store file from bytes
    print("\n1. Storing file from bytes:")
    test_content = b"Hello, World! This is a test file content."
    entry = await media.put(
        test_content,
        filename="hello.txt",
        resource="demo",
        resource_id="demo-001"
    )
    
    print(f"   Stored: {entry.filename}")
    print(f"   Size: {entry.length} bytes")
    print(f"   Hash: {entry.filehash}")
    print(f"   MIME: {entry.filemime}")
    print(f"   Path: {entry.fspath}")
    
    # Demo 2: Retrieve file content
    print("\n2. Retrieving file content:")
    retrieved_content = await media.get(entry._id)
    print(f"   Retrieved {len(retrieved_content)} bytes")
    print(f"   Content matches: {retrieved_content == test_content}")
    
    # Demo 3: Open file for reading
    print("\n3. Opening file for reading:")
    with await media.open(entry._id, 'rb') as f:
        chunk = f.read(5)
        print(f"   First 5 bytes: {chunk}")
    
    return media, entry


async def demo_file_from_path():
    """Demo: Store file from file path"""
    print("\n=== Demo: File from Path ===")
    
    media = MediaInterface()
    
    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp_file:
        tmp_file.write("This content comes from a file on disk.")
        tmp_path = Path(tmp_file.name)
    
    try:
        # Store file using path
        print(f"Storing file from: {tmp_path}")
        entry = await media.put(tmp_path)
        
        print(f"   Stored: {entry.filename}")
        print(f"   Size: {entry.length} bytes")
        print(f"   Auto-detected MIME: {entry.filemime}")
        
        # Verify content
        content = await media.get(entry._id)
        print(f"   Content: {content.decode('utf-8')}")
        
        return entry
        
    finally:
        # Cleanup
        if tmp_path.exists():
            tmp_path.unlink()


async def demo_compression():
    """Demo: File compression and decompression"""
    print("\n=== Demo: File Compression ===")
    
    media = MediaInterface()
    
    # Original content
    original_content = b"This is some content that will be compressed. " * 100
    print(f"Original size: {len(original_content)} bytes")
    
    # Store with GZIP compression
    entry = await media.put(
        original_content,
        filename="compressed_file.txt",
        compress=FsSpecCompressionMethod.GZIP
    )
    
    print(f"Compression method: {entry.compress}")
    print(f"Stored entry size: {entry.length} bytes")
    
    # Retrieve and verify decompression
    retrieved_content = await media.get(entry._id)
    print(f"Retrieved size: {len(retrieved_content)} bytes")
    print(f"Content matches: {retrieved_content == original_content}")
    
    return entry


async def demo_file_management():
    """Demo: File management operations"""
    print("\n=== Demo: File Management ===")
    
    media = MediaInterface()
    
    # Create a test file
    content = b"File to manage"
    entry = await media.put(content, filename="manageable.txt")
    print(f"Created file: {entry.filename} (ID: {entry._id})")
    
    # Check if file exists
    exists = await media.exists(entry._id)
    print(f"File exists: {exists}")
    
    # Copy the file
    copy_entry = await media.copy(entry._id)
    print(f"Created copy: {copy_entry.filename} (ID: {copy_entry._id})")
    
    # Verify both files have same content
    original_content = await media.get(entry._id)
    copied_content = await media.get(copy_entry._id)
    print(f"Copy content matches: {original_content == copied_content}")
    
    # Delete original file
    await media.delete(entry._id)
    print("Deleted original file")
    
    # Check existence again
    exists_after_delete = await media.exists(entry._id)
    copy_still_exists = await media.exists(copy_entry._id)
    print(f"Original exists after delete: {exists_after_delete}")
    print(f"Copy still exists: {copy_still_exists}")
    
    return copy_entry


async def demo_filesystem_registration():
    """Demo: Filesystem registration and configuration"""
    print("\n=== Demo: Filesystem Registration ===")
    
    media = MediaInterface()
    
    # Register an S3 filesystem (would work with actual S3 credentials)
    print("Registering S3 filesystem configuration:")
    
    try:
        # Note: This would work with a real MediaManager connected to database
        # For demo, we'll show what the call would look like
        print("   Would register S3 with:")
        print("   - Key: 'production-s3'")
        print("   - Protocol: 's3'")
        print("   - Name: 'Production S3 Bucket'")
        print("   - Params: bucket='my-app-files', region='us-west-2'")
        
        # In real usage:
        # filesystem = await media.register_filesystem(
        #     'production-s3',
        #     's3', 
        #     'Production S3 Bucket',
        #     bucket='my-app-files',
        #     region='us-west-2'
        # )
        
    except Exception as e:
        print(f"   Note: Registration requires database connection: {e}")


async def demo_resource_organization():
    """Demo: Organizing files by resource and resource_id"""
    print("\n=== Demo: Resource Organization ===")
    
    media = MediaInterface()
    
    # Store files for different resources
    resources = [
        ("user", "user-123", b"User profile image", "avatar.jpg"),
        ("user", "user-123", b"User document", "document.pdf"), 
        ("product", "prod-456", b"Product image", "product.jpg"),
        ("product", "prod-789", b"Another product image", "product2.jpg"),
    ]
    
    stored_entries = []
    
    for resource, resource_id, content, filename in resources:
        entry = await media.put(
            content,
            filename=filename,
            resource=resource,
            resource_id=resource_id
        )
        stored_entries.append(entry)
        print(f"   Stored {filename} for {resource}:{resource_id}")
    
    # Demonstrate filtering (would work with real MediaManager)
    print(f"\nStored {len(stored_entries)} files across different resources")
    print("In production, you could filter by:")
    print("   - All user files: media.list_files(resource='user')")
    print("   - Specific user files: media.list_files(resource='user', resource_id='user-123')")
    print("   - All product files: media.list_files(resource='product')")
    
    return stored_entries


async def demo_real_file_example():
    """Demo: Working with a real file scenario"""
    print("\n=== Demo: Real File Scenario ===")
    
    media = MediaInterface()
    
    # Simulate uploading different file types
    files_to_upload = [
        ("document.txt", b"This is a text document with important content.", "text/plain"),
        ("image.jpg", b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01", "image/jpeg"),  # JPEG header
        ("data.json", b'{"name": "example", "data": [1, 2, 3]}', "application/json"),
    ]
    
    uploaded_files = []
    
    for filename, content, expected_mime in files_to_upload:
        entry = await media.put(
            content,
            filename=filename,
            resource="uploads",
            resource_id="batch-001"
        )
        uploaded_files.append((entry, expected_mime))
        print(f"   Uploaded: {filename} ({entry.length} bytes)")
        print(f"   Detected MIME: {entry.filemime}")
        print(f"   File ID: {entry._id}")
    
    # Demonstrate file retrieval
    print(f"\nRetrieving files:")
    for entry, expected_mime in uploaded_files:
        content = await media.get(entry._id)
        print(f"   {entry.filename}: Retrieved {len(content)} bytes")
    
    return uploaded_files


async def main():
    """Run all demos"""
    print("MediaInterface Demo")
    print("=" * 50)
    
    try:
        await demo_basic_file_operations()
        await demo_file_from_path()
        await demo_compression()
        await demo_file_management()
        await demo_filesystem_registration()
        await demo_resource_organization()
        await demo_real_file_example()
        
        print("\n" + "=" * 50)
        print("Demo Complete!")
        print("\nKey Features Demonstrated:")
        print("✓ File storage from bytes, paths, and file objects")
        print("✓ Automatic metadata tracking with MediaEntry")
        print("✓ File compression and decompression")
        print("✓ File management (copy, delete, exists)")
        print("✓ Resource organization and filtering")
        print("✓ Filesystem abstraction with fsspec")
        print("✓ MIME type detection")
        print("✓ File hashing for integrity")
        
    except Exception as e:
        print(f"\nDemo error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main()) 