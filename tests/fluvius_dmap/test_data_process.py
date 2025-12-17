"""Tests for fluvius.dmap.processor.manager DataModel classes."""
import pytest
from pydantic import ValidationError

from fluvius.dmap.processor.manager import DataProcessEntry


class TestDataProcessEntry:
    """Tests for DataProcessEntry DataModel."""

    def test_basic_creation(self):
        entry = DataProcessEntry(
            file_name='data.csv',
            status='PENDING'
        )
        assert entry.file_name == 'data.csv'
        assert entry.status == 'PENDING'
        assert entry.id is None  # 'id' attribute, aliased as '_id' for serialization
        assert entry.mime_type is None
        assert entry.file_size is None
        assert entry.checksum_sha256 is None
        assert entry.process_name is None

    def test_with_all_fields(self):
        entry = DataProcessEntry(
            _id=1,  # Input uses alias '_id'
            file_name='data.csv',
            mime_type='text/csv',
            file_size=1024,
            checksum_sha256='abc123def456',
            process_name='import_data',
            status='SUCCESS',
            status_message='Completed successfully',
            data_provider='vendor_a',
            data_variant='v1'
        )
        assert entry.id == 1  # Access via 'id' attribute
        assert entry.file_name == 'data.csv'
        assert entry.mime_type == 'text/csv'
        assert entry.file_size == 1024
        assert entry.checksum_sha256 == 'abc123def456'
        assert entry.process_name == 'import_data'
        assert entry.status == 'SUCCESS'
        assert entry.status_message == 'Completed successfully'
        assert entry.data_provider == 'vendor_a'
        assert entry.data_variant == 'v1'

    def test_frozen_model(self):
        """Test that the model is immutable."""
        entry = DataProcessEntry(file_name='test.csv', status='PENDING')
        with pytest.raises(ValidationError):
            entry.status = 'SUCCESS'

    def test_set_method(self):
        """Test that set() returns a new instance with updated values."""
        entry = DataProcessEntry(file_name='test.csv', status='PENDING')
        updated = entry.set(status='SUCCESS')
        
        assert entry.status == 'PENDING'  # Original unchanged
        assert updated.status == 'SUCCESS'  # New instance updated
        assert updated.file_name == 'test.csv'  # Other fields preserved

    def test_set_multiple_fields(self):
        """Test setting multiple fields at once."""
        entry = DataProcessEntry(file_name='test.csv', status='PENDING')
        updated = entry.set(status='SUCCESS', status_message='Done')
        
        assert updated.status == 'SUCCESS'
        assert updated.status_message == 'Done'

    def test_serialize(self):
        """Test serialize() returns a dict without private attrs."""
        entry = DataProcessEntry(
            file_name='data.csv',
            status='PENDING',
            file_size=1024
        )
        data = entry.serialize()
        
        assert isinstance(data, dict)
        assert data['file_name'] == 'data.csv'
        assert data['status'] == 'PENDING'
        assert data['file_size'] == 1024
        # Private attrs should not be in serialized output
        assert '_process_manager' not in data

    def test_serialize_excludes_none(self):
        """Test that serialize() excludes None values by default."""
        entry = DataProcessEntry(file_name='test.csv', status='PENDING')
        data = entry.serialize()
        
        # None values should be excluded
        assert 'mime_type' not in data
        assert 'file_size' not in data
        assert 'checksum_sha256' not in data

    def test_with_process_manager(self):
        """Test creating entry with a process manager."""
        class MockProcessManager:
            def update_entry(self, entry, **kwargs):
                pass

        manager = MockProcessManager()
        entry = DataProcessEntry(
            _process_manager=manager,
            file_name='test.csv',
            status='PENDING'
        )
        
        # Process manager should be accessible as private attr
        assert entry._process_manager is manager

    def test_extra_fields_ignored(self):
        """Test that extra fields are ignored (extra='ignore' config)."""
        entry = DataProcessEntry(
            file_name='test.csv',
            status='PENDING',
            unknown_field='should_be_ignored'
        )
        assert entry.file_name == 'test.csv'
        assert not hasattr(entry, 'unknown_field')

    def test_create_method(self):
        """Test create() class method."""
        entry = DataProcessEntry.create({
            'file_name': 'from_dict.csv',
            'status': 'PENDING'
        })
        assert entry.file_name == 'from_dict.csv'
        assert entry.status == 'PENDING'

    def test_id_serializes_as_underscore_id(self):
        """Test that id field serializes as '_id' (via alias)."""
        entry = DataProcessEntry(_id=42, file_name='test.csv', status='PENDING')
        data = entry.serialize()
        
        assert '_id' in data
        assert data['_id'] == 42


class TestDataProcessEntrySetStatus:
    """Tests for DataProcessEntry.set_status method."""

    def test_set_status_returns_new_entry(self):
        """Test that set_status returns a new entry when status changes."""
        class MockProcessManager:
            def update_entry(self, entry, **kwargs):
                pass

        manager = MockProcessManager()
        entry = DataProcessEntry(
            _process_manager=manager,
            file_name='test.csv',
            status='PENDING'
        )
        
        result = entry.set_status('SUCCESS')
        assert result.status == 'SUCCESS'

    def test_set_status_same_status_returns_self(self):
        """Test that set_status returns same entry when status unchanged."""
        entry = DataProcessEntry(file_name='test.csv', status='PENDING')
        result = entry.set_status('PENDING')
        
        assert result is entry
        assert result.status == 'PENDING'
