import abc
import gzip
import bz2
import lzma
import io
from typing import BinaryIO, Union
from .model import FsSpecCompressionMethod
from ._meta import logger


class MediaCompressor(abc.ABC):
    """Abstract base class for media compression/decompression"""
    
    method: FsSpecCompressionMethod = None
    _compressors: dict[FsSpecCompressionMethod, 'MediaCompressor'] = {}

    def __init_subclass__(cls, **kwargs):
        """Auto-register compressor classes when subclassed"""
        super().__init_subclass__()
        if cls.method in MediaCompressor._compressors:
            raise ValueError(f"Compression method {cls.method} already registered")
        
        MediaCompressor._compressors[cls.method] = cls(**kwargs)

    @classmethod
    def get(cls, method: FsSpecCompressionMethod) -> 'MediaCompressor':
        """Get a compressor instance for the specified method"""
        if method not in cls._compressors:
            raise ValueError(f"Compression method {method} not supported")
        
        return cls._compressors[method]

    @classmethod
    def get_available_methods(cls) -> list[FsSpecCompressionMethod]:
        """Get list of available compression methods"""
        return list(cls._compressors.keys())

    @abc.abstractmethod
    def compress(self, data: bytes) -> bytes:
        """Compress byte data"""
        pass

    @abc.abstractmethod
    def decompress(self, data: bytes) -> bytes:
        """Decompress byte data"""
        pass

    @abc.abstractmethod
    def open_compressed(self, data: bytes) -> BinaryIO:
        """Open compressed data as a file-like object for reading"""
        pass

    @abc.abstractmethod
    def compress_stream(self, input_stream: BinaryIO) -> bytes:
        """Compress data from an input stream"""
        pass

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.method})"


class GzipCompressor(MediaCompressor):
    """GZIP compression implementation"""
    
    method = FsSpecCompressionMethod.GZIP

    def compress(self, data: bytes) -> bytes:
        """Compress data using GZIP"""
        try:
            return gzip.compress(data)
        except Exception as e:
            logger.error(f"GZIP compression failed: {e}")
            raise ValueError(f"Failed to compress data with GZIP: {e}")

    def decompress(self, data: bytes) -> bytes:
        """Decompress GZIP data"""
        try:
            return gzip.decompress(data)
        except Exception as e:
            logger.error(f"GZIP decompression failed: {e}")
            raise ValueError(f"Failed to decompress GZIP data: {e}")

    def open_compressed(self, data: bytes) -> BinaryIO:
        """Open GZIP compressed data as file-like object"""
        try:
            file_obj = gzip.open(io.BytesIO(data), 'rb')
            # Validate by attempting to read header - this triggers format validation
            pos = file_obj.tell()
            file_obj.read(1)  # Try to read one byte to trigger validation
            file_obj.seek(pos)  # Reset position
            return file_obj
        except Exception as e:
            logger.error(f"Failed to open GZIP data: {e}")
            raise ValueError(f"Failed to open GZIP compressed data: {e}")

    def compress_stream(self, input_stream: BinaryIO) -> bytes:
        """Compress data from input stream using GZIP"""
        try:
            # Read all data from stream
            data = input_stream.read()
            return self.compress(data)
        except Exception as e:
            logger.error(f"GZIP stream compression failed: {e}")
            raise ValueError(f"Failed to compress stream with GZIP: {e}")


class Bz2Compressor(MediaCompressor):
    """BZ2 compression implementation"""
    
    method = FsSpecCompressionMethod.BZ2

    def compress(self, data: bytes) -> bytes:
        """Compress data using BZ2"""
        try:
            return bz2.compress(data)
        except Exception as e:
            logger.error(f"BZ2 compression failed: {e}")
            raise ValueError(f"Failed to compress data with BZ2: {e}")

    def decompress(self, data: bytes) -> bytes:
        """Decompress BZ2 data"""
        try:
            return bz2.decompress(data)
        except Exception as e:
            logger.error(f"BZ2 decompression failed: {e}")
            raise ValueError(f"Failed to decompress BZ2 data: {e}")

    def open_compressed(self, data: bytes) -> BinaryIO:
        """Open BZ2 compressed data as file-like object"""
        try:
            file_obj = bz2.open(io.BytesIO(data), 'rb')
            # Validate by attempting to read header - this triggers format validation
            pos = file_obj.tell()
            file_obj.read(1)  # Try to read one byte to trigger validation
            file_obj.seek(pos)  # Reset position
            return file_obj
        except Exception as e:
            logger.error(f"Failed to open BZ2 data: {e}")
            raise ValueError(f"Failed to open BZ2 compressed data: {e}")

    def compress_stream(self, input_stream: BinaryIO) -> bytes:
        """Compress data from input stream using BZ2"""
        try:
            data = input_stream.read()
            return self.compress(data)
        except Exception as e:
            logger.error(f"BZ2 stream compression failed: {e}")
            raise ValueError(f"Failed to compress stream with BZ2: {e}")


class LzmaCompressor(MediaCompressor):
    """LZMA compression implementation"""
    
    method = FsSpecCompressionMethod.LZMA

    def compress(self, data: bytes) -> bytes:
        """Compress data using LZMA"""
        try:
            return lzma.compress(data)
        except Exception as e:
            logger.error(f"LZMA compression failed: {e}")
            raise ValueError(f"Failed to compress data with LZMA: {e}")

    def decompress(self, data: bytes) -> bytes:
        """Decompress LZMA data"""
        try:
            return lzma.decompress(data)
        except Exception as e:
            logger.error(f"LZMA decompression failed: {e}")
            raise ValueError(f"Failed to decompress LZMA data: {e}")

    def open_compressed(self, data: bytes) -> BinaryIO:
        """Open LZMA compressed data as file-like object"""
        try:
            file_obj = lzma.open(io.BytesIO(data), 'rb')
            # Validate by attempting to read header - this triggers format validation
            pos = file_obj.tell()
            file_obj.read(1)  # Try to read one byte to trigger validation
            file_obj.seek(pos)  # Reset position
            return file_obj
        except Exception as e:
            logger.error(f"Failed to open LZMA data: {e}")
            raise ValueError(f"Failed to open LZMA compressed data: {e}")

    def compress_stream(self, input_stream: BinaryIO) -> bytes:
        """Compress data from input stream using LZMA"""
        try:
            data = input_stream.read()
            return self.compress(data)
        except Exception as e:
            logger.error(f"LZMA stream compression failed: {e}")
            raise ValueError(f"Failed to compress stream with LZMA: {e}")


class NullCompressor(MediaCompressor):
    """No-op compressor for uncompressed data"""
    
    method = None  # Special case - doesn't auto-register

    def compress(self, data: bytes) -> bytes:
        """Return data unchanged"""
        return data

    def decompress(self, data: bytes) -> bytes:
        """Return data unchanged"""
        return data

    def open_compressed(self, data: bytes) -> BinaryIO:
        """Return data as BytesIO"""
        return io.BytesIO(data)

    def compress_stream(self, input_stream: BinaryIO) -> bytes:
        """Read and return stream data unchanged"""
        return input_stream.read()



# Export the main classes and functions
__all__ = [
    'MediaCompressor'
]

