import pytest
import io
from fluvius.media.compressor import (
    MediaCompressor,
    GzipCompressor,
    Bz2Compressor, 
    LzmaCompressor,
    NullCompressor
)
from fluvius.media.model import FsSpecCompressionMethod


class TestMediaCompressor:
    """Test suite for MediaCompressor base class and registry"""
    
    def test_compressor_registration(self):
        """Test that compressors are automatically registered"""
        available_methods = MediaCompressor.get_available_methods()
        
        assert FsSpecCompressionMethod.GZIP in available_methods
        assert FsSpecCompressionMethod.BZ2 in available_methods
        assert FsSpecCompressionMethod.LZMA in available_methods
        
    def test_get_compressor(self):
        """Test getting compressor instances"""
        gzip_compressor = MediaCompressor.get(FsSpecCompressionMethod.GZIP)
        assert isinstance(gzip_compressor, GzipCompressor)
        
        bz2_compressor = MediaCompressor.get(FsSpecCompressionMethod.BZ2)
        assert isinstance(bz2_compressor, Bz2Compressor)
        
        lzma_compressor = MediaCompressor.get(FsSpecCompressionMethod.LZMA)
        assert isinstance(lzma_compressor, LzmaCompressor)
    
    def test_unsupported_method(self):
        """Test that unsupported methods raise ValueError"""
        with pytest.raises(ValueError, match="Compression method.*not supported"):
            MediaCompressor.get("unsupported_method")


class TestGzipCompressor:
    """Test suite for GZIP compression"""
    
    @pytest.fixture
    def compressor(self):
        return GzipCompressor()
    
    @pytest.fixture
    def test_data(self):
        return b"Hello, World! This is test data for GZIP compression."
    
    def test_compress_decompress(self, compressor, test_data):
        """Test compression and decompression cycle"""
        # Compress
        compressed = compressor.compress(test_data)
        assert compressed != test_data
        assert len(compressed) > 0
        
        # Decompress
        decompressed = compressor.decompress(compressed)
        assert decompressed == test_data
    
    def test_open_compressed(self, compressor, test_data):
        """Test opening compressed data as file-like object"""
        compressed = compressor.compress(test_data)
        
        # Open as file-like object
        with compressor.open_compressed(compressed) as f:
            decompressed = f.read()
        
        assert decompressed == test_data
    
    def test_compress_stream(self, compressor, test_data):
        """Test compressing from stream"""
        input_stream = io.BytesIO(test_data)
        
        compressed = compressor.compress_stream(input_stream)
        decompressed = compressor.decompress(compressed)
        
        assert decompressed == test_data
    
    def test_empty_data(self, compressor):
        """Test compression of empty data"""
        empty_data = b""
        compressed = compressor.compress(empty_data)
        decompressed = compressor.decompress(compressed)
        
        assert decompressed == empty_data
    
    def test_large_data(self, compressor):
        """Test compression of larger data"""
        large_data = b"A" * 10000 + b"B" * 10000 + b"C" * 10000
        compressed = compressor.compress(large_data)
        decompressed = compressor.decompress(compressed)
        
        assert decompressed == large_data
        # GZIP should compress repeated data well
        assert len(compressed) < len(large_data)


class TestBz2Compressor:
    """Test suite for BZ2 compression"""
    
    @pytest.fixture
    def compressor(self):
        return Bz2Compressor()
    
    @pytest.fixture
    def test_data(self):
        return b"Hello, World! This is test data for BZ2 compression."
    
    def test_compress_decompress(self, compressor, test_data):
        """Test compression and decompression cycle"""
        compressed = compressor.compress(test_data)
        assert compressed != test_data
        assert len(compressed) > 0
        
        decompressed = compressor.decompress(compressed)
        assert decompressed == test_data
    
    def test_open_compressed(self, compressor, test_data):
        """Test opening compressed data as file-like object"""
        compressed = compressor.compress(test_data)
        
        with compressor.open_compressed(compressed) as f:
            decompressed = f.read()
        
        assert decompressed == test_data
    
    def test_compress_stream(self, compressor, test_data):
        """Test compressing from stream"""
        input_stream = io.BytesIO(test_data)
        
        compressed = compressor.compress_stream(input_stream)
        decompressed = compressor.decompress(compressed)
        
        assert decompressed == test_data


class TestLzmaCompressor:
    """Test suite for LZMA compression"""
    
    @pytest.fixture
    def compressor(self):
        return LzmaCompressor()
    
    @pytest.fixture
    def test_data(self):
        return b"Hello, World! This is test data for LZMA compression."
    
    def test_compress_decompress(self, compressor, test_data):
        """Test compression and decompression cycle"""
        compressed = compressor.compress(test_data)
        assert compressed != test_data
        assert len(compressed) > 0
        
        decompressed = compressor.decompress(compressed)
        assert decompressed == test_data
    
    def test_open_compressed(self, compressor, test_data):
        """Test opening compressed data as file-like object"""
        compressed = compressor.compress(test_data)
        
        with compressor.open_compressed(compressed) as f:
            decompressed = f.read()
        
        assert decompressed == test_data
    
    def test_compress_stream(self, compressor, test_data):
        """Test compressing from stream"""
        input_stream = io.BytesIO(test_data)
        
        compressed = compressor.compress_stream(input_stream)
        decompressed = compressor.decompress(compressed)
        
        assert decompressed == test_data


class TestNullCompressor:
    """Test suite for NullCompressor (no-op)"""
    
    @pytest.fixture
    def compressor(self):
        return NullCompressor()
    
    @pytest.fixture
    def test_data(self):
        return b"This data should not be modified by NullCompressor."
    
    def test_compress_no_change(self, compressor, test_data):
        """Test that compression returns data unchanged"""
        result = compressor.compress(test_data)
        assert result == test_data
        assert result is test_data  # Should be the exact same object
    
    def test_decompress_no_change(self, compressor, test_data):
        """Test that decompression returns data unchanged"""
        result = compressor.decompress(test_data)
        assert result == test_data
        assert result is test_data  # Should be the exact same object
    
    def test_open_compressed_as_bytesio(self, compressor, test_data):
        """Test that open_compressed returns BytesIO"""
        file_obj = compressor.open_compressed(test_data)
        assert isinstance(file_obj, io.BytesIO)
        
        content = file_obj.read()
        assert content == test_data
    
    def test_compress_stream(self, compressor, test_data):
        """Test that compress_stream reads and returns data unchanged"""
        input_stream = io.BytesIO(test_data)
        result = compressor.compress_stream(input_stream)
        assert result == test_data


class TestConvenienceFunctions:
    """Test suite for convenience functions"""
    
    @pytest.fixture
    def test_data(self):
        return b"Test data for convenience functions."
    
    def test_compress_data_function(self, test_data):
        """Test compress_data convenience function"""
        compressed = MediaCompressor.get(FsSpecCompressionMethod.GZIP).compress(test_data)
        assert compressed != test_data
        assert len(compressed) > 0
    
    def test_decompress_data_function(self, test_data):
        """Test decompress_data convenience function"""
        compressor = MediaCompressor.get(FsSpecCompressionMethod.GZIP)
        compressed = compressor.compress(test_data)
        decompressed = compressor.decompress(compressed)
        assert decompressed == test_data
    
    def test_open_compressed_data_function(self, test_data):
        """Test open_compressed_data convenience function"""
        compressor = MediaCompressor.get(FsSpecCompressionMethod.GZIP)
        compressed = compressor.compress(test_data)
        
        with compressor.open_compressed(compressed) as f:
            decompressed = f.read()
        
        assert decompressed == test_data
    
    def test_get_compressor_function(self):
        """Test get_compressor convenience function"""
        compressor = MediaCompressor.get(FsSpecCompressionMethod.BZ2)
        assert isinstance(compressor, Bz2Compressor)


class TestCompressionComparison:
    """Test suite for comparing different compression methods"""
    
    @pytest.fixture
    def test_data(self):
        # Data with patterns that should compress well
        return b"AAAAAAAAAA" * 1000 + b"BBBBBBBBBB" * 1000 + b"CCCCCCCCCC" * 1000
    
    def test_all_methods_work(self, test_data):
        """Test that all compression methods work correctly"""
        methods = [
            FsSpecCompressionMethod.GZIP,
            FsSpecCompressionMethod.BZ2,
            FsSpecCompressionMethod.LZMA
        ]
        
        for method in methods:
            compressor = MediaCompressor.get(method)
            compressed = compressor.compress(test_data)
            decompressed = compressor.decompress(compressed)
            
            assert decompressed == test_data
            assert len(compressed) < len(test_data)  # Should compress well
    
    def test_compression_ratios(self, test_data):
        """Test compression ratios for different methods"""
        original_size = len(test_data)
        bz2 = MediaCompressor.get(FsSpecCompressionMethod.BZ2)
        gzip = MediaCompressor.get(FsSpecCompressionMethod.GZIP)
        lzma = MediaCompressor.get(FsSpecCompressionMethod.LZMA)
        gzip_size = len(gzip.compress(test_data))
        bz2_size = len(bz2.compress(test_data))
        lzma_size = len(lzma.compress(test_data))
        
        # All should compress the repetitive data significantly
        assert gzip_size < original_size * 0.1  # Less than 10% of original
        assert bz2_size < original_size * 0.1
        assert lzma_size < original_size * 0.1
        
        print(f"Original: {original_size} bytes")
        print(f"GZIP: {gzip_size} bytes ({gzip_size/original_size*100:.1f}%)")
        print(f"BZ2: {bz2_size} bytes ({bz2_size/original_size*100:.1f}%)")
        print(f"LZMA: {lzma_size} bytes ({lzma_size/original_size*100:.1f}%)")


class TestErrorHandling:
    """Test suite for error handling in compressors"""
    
    def test_invalid_compressed_data(self):
        """Test handling of invalid compressed data"""
        invalid_data = b"This is not compressed data"
        
        gzip_compressor = GzipCompressor()
        with pytest.raises(ValueError, match="Failed to decompress GZIP data"):
            gzip_compressor.decompress(invalid_data)
        
        bz2_compressor = Bz2Compressor()
        with pytest.raises(ValueError, match="Failed to decompress BZ2 data"):
            bz2_compressor.decompress(invalid_data)
        
        lzma_compressor = LzmaCompressor()
        with pytest.raises(ValueError, match="Failed to decompress LZMA data"):
            lzma_compressor.decompress(invalid_data)
    
    def test_invalid_open_compressed(self):
        """Test handling of invalid data in open_compressed"""
        invalid_data = b"This is not compressed data"
        
        gzip_compressor = GzipCompressor()
        with pytest.raises(ValueError, match="Failed to open GZIP compressed data"):
            gzip_compressor.open_compressed(invalid_data)
        
        bz2_compressor = Bz2Compressor()
        with pytest.raises(ValueError, match="Failed to open BZ2 compressed data"):
            bz2_compressor.open_compressed(invalid_data)
        
        lzma_compressor = LzmaCompressor()
        with pytest.raises(ValueError, match="Failed to open LZMA compressed data"):
            lzma_compressor.open_compressed(invalid_data)


class TestCompressorStrRepresentation:
    """Test string representation of compressors"""
    
    def test_compressor_str(self):
        """Test string representation of compressor instances"""
        gzip_compressor = GzipCompressor()
        assert str(gzip_compressor) == f"GzipCompressor({FsSpecCompressionMethod.GZIP})"
        
        bz2_compressor = Bz2Compressor()
        assert str(bz2_compressor) == f"Bz2Compressor({FsSpecCompressionMethod.BZ2})"
        
        lzma_compressor = LzmaCompressor()
        assert str(lzma_compressor) == f"LzmaCompressor({FsSpecCompressionMethod.LZMA})"
        
        null_compressor = NullCompressor()
        assert str(null_compressor) == "NullCompressor(None)" 
