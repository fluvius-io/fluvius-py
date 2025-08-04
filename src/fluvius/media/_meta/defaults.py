DEFAULT_FILESYSTEM = 'file'
FILESYSTEM_PARAMS = {
    'user': 'admin'
}
FILESYSTEM_ROOT = 'root'

# Database configuration
MEDIA_DB_DSN = 'sqlite+aiosqlite:////tmp/fluvius_media.sqlite'
MEDIA_DB_SCHEMA = 'fluvius_media'

# Default file storage settings
DEFAULT_COMPRESSION = None
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
CHUNK_SIZE = 1024 * 1024  # 1MB
TEMP_DIR = '/tmp/fluvius_media_temp'
