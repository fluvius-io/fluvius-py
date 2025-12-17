"""Tests for fluvius.dmap.interface DataModel classes."""
import pytest
from pydantic import ValidationError

from fluvius.dmap.interface import (
    ReaderConfig,
    WriterConfig,
    PipelineConfig,
    DataProcessManagerConfig,
    DataProcessConfig,
    InputFile,
    DataElement,
    DataLoop,
    DataObject,
    InputResourceKind,
)


class TestReaderConfig:
    """Tests for ReaderConfig DataModel."""

    def test_basic_creation(self):
        config = ReaderConfig(name='csv_reader')
        assert config.name == 'csv_reader'
        assert config.debug_log is None
        assert config.error_log is None
        assert config.transforms == []

    def test_with_all_fields(self):
        config = ReaderConfig(
            name='csv_reader',
            debug_log='/tmp/debug.log',
            error_log='/tmp/error.log',
            transforms=['uppercase', 'trim']
        )
        assert config.name == 'csv_reader'
        assert config.debug_log == '/tmp/debug.log'
        assert config.error_log == '/tmp/error.log'
        assert config.transforms == ['uppercase', 'trim']

    def test_transforms_string_to_list(self):
        """Test that a single string transform is converted to a list."""
        config = ReaderConfig(name='test', transforms='single_transform')
        assert config.transforms == ['single_transform']

    def test_transforms_tuple_to_list(self):
        """Test that tuple transforms are converted to a list."""
        config = ReaderConfig(name='test', transforms=('a', 'b'))
        assert config.transforms == ['a', 'b']

    def test_frozen_model(self):
        """Test that the model is immutable."""
        config = ReaderConfig(name='test')
        with pytest.raises(ValidationError):
            config.name = 'changed'

    def test_set_method(self):
        """Test that set() returns a new instance with updated values."""
        config = ReaderConfig(name='original')
        updated = config.set(name='updated')
        
        assert config.name == 'original'  # Original unchanged
        assert updated.name == 'updated'  # New instance has updated value

    def test_create_method_from_dict(self):
        """Test create() with a dictionary."""
        config = ReaderConfig.create({'name': 'from_dict'})
        assert config.name == 'from_dict'

    def test_create_method_with_kwargs(self):
        """Test create() with keyword arguments."""
        config = ReaderConfig.create(name='from_kwargs')
        assert config.name == 'from_kwargs'

    def test_create_method_with_defaults(self):
        """Test create() with defaults parameter."""
        config = ReaderConfig.create(
            {'name': 'test'},
            defaults={'debug_log': '/tmp/default.log'}
        )
        assert config.name == 'test'
        assert config.debug_log == '/tmp/default.log'

    def test_serialize(self):
        """Test serialize() returns a dict."""
        config = ReaderConfig(name='test', debug_log='/tmp/log')
        data = config.serialize()
        
        assert isinstance(data, dict)
        assert data['name'] == 'test'
        assert data['debug_log'] == '/tmp/log'


class TestWriterConfig:
    """Tests for WriterConfig DataModel."""

    def test_basic_creation(self):
        config = WriterConfig(name='csv_writer')
        assert config.name == 'csv_writer'
        assert config.transforms == []

    def test_transforms_validation(self):
        """Test that transforms are validated correctly."""
        config = WriterConfig(name='test', transforms='single')
        assert config.transforms == ['single']

    def test_inheritance_from_data_model(self):
        """Test that set() and serialize() work."""
        config = WriterConfig(name='test')
        
        updated = config.set(name='updated')
        assert updated.name == 'updated'
        
        data = config.serialize()
        assert data['name'] == 'test'


class TestPipelineConfig:
    """Tests for PipelineConfig DataModel."""

    def test_basic_creation(self):
        config = PipelineConfig(key='pipeline1', mapping={'a': 'b'})
        assert config.key == 'pipeline1'
        assert config.mapping == {'a': 'b'}
        assert config.transaction is None
        assert config.transforms == []
        assert config.writer == {}
        assert config.coercer_profile == 'generic'
        assert config.allow_ctx_buffer is True

    def test_with_all_fields(self):
        config = PipelineConfig(
            key='pipeline1',
            transaction='tx1',
            mapping={'source': 'target'},
            transforms=['normalize', 'validate'],
            writer={'name': 'sql', 'uri': 'postgresql://localhost/db'},
            coercer_profile='strict',
            allow_ctx_buffer=False
        )
        assert config.key == 'pipeline1'
        assert config.transaction == 'tx1'
        assert config.transforms == ['normalize', 'validate']
        assert config.writer == {'name': 'sql', 'uri': 'postgresql://localhost/db'}
        assert config.coercer_profile == 'strict'
        assert config.allow_ctx_buffer is False

    def test_writer_string_to_dict(self):
        """Test that a string writer is converted to a dict."""
        config = PipelineConfig(key='test', mapping={}, writer='sql')
        assert config.writer == {'name': 'sql'}

    def test_transforms_string_to_list(self):
        """Test that a single transform string is converted to a list."""
        config = PipelineConfig(key='test', mapping={}, transforms='single')
        assert config.transforms == ['single']


class TestDataProcessManagerConfig:
    """Tests for DataProcessManagerConfig DataModel."""

    def test_basic_creation(self):
        config = DataProcessManagerConfig(
            name='postgres',
            process_name='import_data',
            process_tracker={'uri': 'postgresql://localhost/db', 'table': 'process_log'}
        )
        assert config.name == 'postgres'
        assert config.process_name == 'import_data'
        assert config.process_tracker == {'uri': 'postgresql://localhost/db', 'table': 'process_log'}
        assert config.force_import is False

    def test_with_force_import(self):
        config = DataProcessManagerConfig(
            name='postgres',
            process_name='import_data',
            process_tracker={},
            force_import=True
        )
        assert config.force_import is True

    def test_missing_required_fields(self):
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError):
            DataProcessManagerConfig(name='test')


class TestDataProcessConfig:
    """Tests for DataProcessConfig DataModel."""

    def test_default_values(self):
        config = DataProcessConfig()
        assert config.inputs == {}
        assert config.manager is None
        assert config.reader == {}
        assert config.writer == {}
        assert config.pipelines == {}
        assert config.metadata == {}

    def test_with_manager(self):
        config = DataProcessConfig(
            manager={
                'name': 'postgres',
                'process_name': 'import',
                'process_tracker': {'uri': 'pg://localhost'}
            }
        )
        assert isinstance(config.manager, DataProcessManagerConfig)
        assert config.manager.name == 'postgres'
        assert config.manager.process_name == 'import'

    def test_inputs_string_to_dict(self):
        """Test that inputs string is converted to dict with name key."""
        config = DataProcessConfig(inputs='file_input')
        assert config.inputs == {'name': 'file_input'}

    def test_writer_string_to_dict(self):
        """Test that writer string is converted to dict with name key."""
        config = DataProcessConfig(writer='sql')
        assert config.writer == {'name': 'sql'}


class TestInputFile:
    """Tests for InputFile DataModel."""

    def test_basic_creation(self):
        input_file = InputFile(
            filename='data.csv',
            filepath='/tmp/data.csv'
        )
        assert input_file.filename == 'data.csv'
        assert input_file.filepath == '/tmp/data.csv'
        assert input_file.filesize is None
        assert input_file.filetype is None
        assert input_file.source_id is None
        assert input_file.sha256sum is None
        assert input_file.metadata is None

    def test_with_all_fields(self):
        input_file = InputFile(
            filename='data.csv',
            filepath='/tmp/data.csv',
            filesize=1024,
            filetype='text/csv',
            source_id=42,
            sha256sum='abc123',
            metadata={'created': '2024-01-01'}
        )
        assert input_file.filename == 'data.csv'
        assert input_file.filesize == 1024
        assert input_file.filetype == 'text/csv'
        assert input_file.source_id == 42
        assert input_file.sha256sum == 'abc123'
        assert input_file.metadata == {'created': '2024-01-01'}

    def test_set_method(self):
        """Test set() creates a new instance with updated values."""
        input_file = InputFile(filename='original.csv', filepath='/tmp/original.csv')
        updated = input_file.set(filename='updated.csv')
        
        assert input_file.filename == 'original.csv'
        assert updated.filename == 'updated.csv'
        assert updated.filepath == '/tmp/original.csv'  # Unchanged

    def test_serialize(self):
        """Test serialize() returns a dict."""
        input_file = InputFile(
            filename='data.csv',
            filepath='/tmp/data.csv',
            filesize=1024
        )
        data = input_file.serialize()
        
        assert isinstance(data, dict)
        assert data['filename'] == 'data.csv'
        assert data['filepath'] == '/tmp/data.csv'
        assert data['filesize'] == 1024


class TestNamedTuples:
    """Tests for namedtuple types in interface."""

    def test_data_element(self):
        elem = DataElement(key='name', value='John')
        assert elem.key == 'name'
        assert elem.value == 'John'
        assert elem.meta is None

    def test_data_element_with_meta(self):
        elem = DataElement(key='age', value=30, meta={'type': 'integer'})
        assert elem.key == 'age'
        assert elem.value == 30
        assert elem.meta == {'type': 'integer'}

    def test_data_loop(self):
        loop = DataLoop(id='loop1', elements=[DataElement('a', 1)], depth=1)
        assert loop.id == 'loop1'
        assert len(loop.elements) == 1
        assert loop.depth == 1
        assert loop.meta is None

    def test_data_object(self):
        obj = DataObject(index=0, object={'name': 'test'}, context=[])
        assert obj.index == 0
        assert obj.object == {'name': 'test'}
        assert obj.context == []


class TestInputResourceKind:
    """Tests for InputResourceKind enum."""

    def test_enum_values(self):
        assert InputResourceKind.FILE.value == 'FILE'
        assert InputResourceKind.S3FILE.value == 'S3FILE'
        assert InputResourceKind.REST_API.value == 'REST_API'
