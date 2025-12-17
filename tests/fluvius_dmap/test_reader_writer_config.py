"""Tests for fluvius.dmap reader and writer DataModel classes."""
import pytest
from pydantic import ValidationError

from fluvius.dmap.reader.tabular import TabularReaderConfig
from fluvius.dmap.writer.base import FileWriterConfig, WriterConfig
from fluvius.dmap.vendor.writer_sql import SQLWriterConfig


class TestTabularReaderConfig:
    """Tests for TabularReaderConfig DataModel."""

    def test_basic_creation(self):
        config = TabularReaderConfig(name='csv_reader')
        assert config.name == 'csv_reader'
        assert config.required_headers is None
        assert config.required_fields is None
        assert config.no_headers is False
        assert config.ignore_invalid_rows is False
        assert config.trim_spaces is False
        assert config.null_values is None

    def test_with_all_fields(self):
        config = TabularReaderConfig(
            name='csv_reader',
            debug_log='/tmp/debug.log',
            error_log='/tmp/error.log',
            transforms=['trim', 'uppercase'],
            required_headers=['name', 'email', 'age'],
            required_fields=['name', 'email'],
            no_headers=False,
            ignore_invalid_rows=True,
            trim_spaces=True,
            null_values=['', 'NULL', 'N/A']
        )
        assert config.name == 'csv_reader'
        assert config.debug_log == '/tmp/debug.log'
        assert config.transforms == ['trim', 'uppercase']
        assert config.required_headers == ['name', 'email', 'age']
        assert config.required_fields == ['name', 'email']
        assert config.ignore_invalid_rows is True
        assert config.trim_spaces is True
        assert config.null_values == ['', 'NULL', 'N/A']

    def test_no_headers_requires_required_headers(self):
        """Test that no_headers=True requires required_headers to be set."""
        with pytest.raises(ValidationError) as exc_info:
            TabularReaderConfig(name='test', no_headers=True)
        
        assert 'required_headers' in str(exc_info.value)

    def test_no_headers_with_required_headers(self):
        """Test that no_headers=True works when required_headers is provided."""
        config = TabularReaderConfig(
            name='test',
            no_headers=True,
            required_headers=['col1', 'col2', 'col3']
        )
        assert config.no_headers is True
        assert config.required_headers == ['col1', 'col2', 'col3']

    def test_inherits_from_reader_config(self):
        """Test that TabularReaderConfig inherits ReaderConfig fields."""
        config = TabularReaderConfig(
            name='test',
            debug_log='/tmp/debug.log',
            error_log='/tmp/error.log',
            transforms=['uppercase']
        )
        assert config.debug_log == '/tmp/debug.log'
        assert config.error_log == '/tmp/error.log'
        assert config.transforms == ['uppercase']

    def test_transforms_string_to_list(self):
        """Test that transforms string is converted to list (inherited behavior)."""
        config = TabularReaderConfig(name='test', transforms='single_transform')
        assert config.transforms == ['single_transform']

    def test_frozen_model(self):
        """Test that the model is immutable."""
        config = TabularReaderConfig(name='test')
        with pytest.raises(ValidationError):
            config.trim_spaces = True

    def test_set_method(self):
        """Test set() returns a new instance with updated values."""
        config = TabularReaderConfig(name='test', trim_spaces=False)
        updated = config.set(trim_spaces=True)
        
        assert config.trim_spaces is False
        assert updated.trim_spaces is True


class TestFileWriterConfig:
    """Tests for FileWriterConfig DataModel."""

    def test_basic_creation(self):
        config = FileWriterConfig(name='csv_writer')
        assert config.name == 'csv_writer'
        assert config.path is None
        assert config.csv_dialect == 'csvquote'
        assert config.file_extension is None
        assert config.db_schema is None

    def test_with_all_fields(self):
        config = FileWriterConfig(
            name='csv_writer',
            transforms=['format_dates'],
            path='/tmp/output',
            csv_dialect='excel',
            file_extension='.csv',
            db_schema='public'
        )
        assert config.name == 'csv_writer'
        assert config.transforms == ['format_dates']
        assert config.path == '/tmp/output'
        assert config.csv_dialect == 'excel'
        assert config.file_extension == '.csv'
        assert config.db_schema == 'public'

    def test_inherits_from_writer_config(self):
        """Test that FileWriterConfig inherits WriterConfig fields."""
        config = FileWriterConfig(name='test', transforms=['transform1', 'transform2'])
        assert config.name == 'test'
        assert config.transforms == ['transform1', 'transform2']

    def test_transforms_string_to_list(self):
        """Test that transforms string is converted to list (inherited behavior)."""
        config = FileWriterConfig(name='test', transforms='single')
        assert config.transforms == ['single']

    def test_frozen_model(self):
        """Test that the model is immutable."""
        config = FileWriterConfig(name='test')
        with pytest.raises(ValidationError):
            config.path = '/new/path'

    def test_set_method(self):
        """Test set() returns a new instance with updated values."""
        config = FileWriterConfig(name='test', path='/original')
        updated = config.set(path='/updated')
        
        assert config.path == '/original'
        assert updated.path == '/updated'


class TestSQLWriterConfig:
    """Tests for SQLWriterConfig DataModel."""

    def test_basic_creation(self):
        config = SQLWriterConfig(
            name='sql_writer',
            uri='postgresql://localhost/db',
            db_schema='public'
        )
        assert config.name == 'sql_writer'
        assert config.uri == 'postgresql://localhost/db'
        assert config.db_schema == 'public'
        assert config.mode == 'append'

    def test_with_all_fields(self):
        config = SQLWriterConfig(
            name='sql_writer',
            transforms=['normalize'],
            uri='postgresql://user:pass@localhost:5432/mydb',
            db_schema='data_import',
            mode='replace'
        )
        assert config.name == 'sql_writer'
        assert config.transforms == ['normalize']
        assert config.uri == 'postgresql://user:pass@localhost:5432/mydb'
        assert config.db_schema == 'data_import'
        assert config.mode == 'replace'

    def test_missing_required_fields(self):
        """Test that uri and db_schema are required."""
        with pytest.raises(ValidationError):
            SQLWriterConfig(name='test')
        
        with pytest.raises(ValidationError):
            SQLWriterConfig(name='test', uri='pg://localhost')
        
        with pytest.raises(ValidationError):
            SQLWriterConfig(name='test', db_schema='public')

    def test_inherits_from_writer_config(self):
        """Test that SQLWriterConfig inherits WriterConfig fields."""
        config = SQLWriterConfig(
            name='test',
            transforms=['transform1'],
            uri='postgresql://localhost/db',
            db_schema='public'
        )
        assert config.transforms == ['transform1']

    def test_frozen_model(self):
        """Test that the model is immutable."""
        config = SQLWriterConfig(
            name='test',
            uri='postgresql://localhost/db',
            db_schema='public'
        )
        with pytest.raises(ValidationError):
            config.mode = 'replace'

    def test_set_method(self):
        """Test set() returns a new instance with updated values."""
        config = SQLWriterConfig(
            name='test',
            uri='postgresql://localhost/db',
            db_schema='public',
            mode='append'
        )
        updated = config.set(mode='replace')
        
        assert config.mode == 'append'
        assert updated.mode == 'replace'

    def test_serialize(self):
        """Test serialize() returns a dict."""
        config = SQLWriterConfig(
            name='sql_writer',
            uri='postgresql://localhost/db',
            db_schema='public'
        )
        data = config.serialize()
        
        assert isinstance(data, dict)
        assert data['name'] == 'sql_writer'
        assert data['uri'] == 'postgresql://localhost/db'
        assert data['db_schema'] == 'public'
        assert data['mode'] == 'append'

