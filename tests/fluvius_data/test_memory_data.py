import pytest
from datetime import datetime
from typing import Optional
from pydantic import Field

from fluvius.data import logger, timestamp, field, DataModel
from fluvius.data.data_driver import InMemoryDriver
from fluvius.data.query import BackendQuery
from fluvius.data.data_manager import DataAccessManager
from fluvius.data.exceptions import ItemNotFoundError


class TestMemoryConnector(InMemoryDriver):
    pass


class MemoryAccessManager(DataAccessManager):
    __connector__ = TestMemoryConnector
    __automodel__ = False  # We'll define our own models

    @classmethod
    def _serialize(cls, model_name, item):
        """Override to use model_dump() for Pydantic models"""
        if hasattr(item, 'model_dump'):
            result = item.model_dump()  # Include None values
            return result
        elif hasattr(item, 'serialize'):
            return item.serialize()
        elif isinstance(item, dict):
            return item
        else:
            return item.__dict__


@MemoryAccessManager.register_model('demo-resource')
class DemoDataResource(DataModel):
    id: str = Field(alias='_id')
    name: Optional[str] = None
    value: int = 0
    created: Optional[datetime] = Field(default=None, alias='_created')
    updated: Optional[datetime] = Field(default=None, alias='_updated')
    deleted: Optional[datetime] = Field(default=None, alias='_deleted')
    
    model_config = {"populate_by_name": True}


@pytest.mark.asyncio
async def test_memory_driver_basic_operations():
    """Test basic CRUD operations with memory driver"""
    manager = MemoryAccessManager(None)
    
    # Test Create and Insert
    data = {
        '_id': 'test-001', 
        'name': 'Test Item', 
        'value': 42
    }
    
    demo_record = manager.create('demo-resource', data)
    
    async with manager.transaction():
        result = await manager.insert(demo_record)
        # Insert returns the serialized data (dict), not the original record
        assert '_id' in result
        assert result['_id'] == 'test-001'
    
    # Test Fetch - this should return a wrapped model
    fetched = await manager.fetch('demo-resource', 'test-001')
    assert fetched.id == 'test-001'
    assert fetched.name == 'Test Item'
    assert fetched.value == 42
    
    # Test Update
    async with manager.transaction():
        await manager.update_one('demo-resource', 'test-001', name='Updated Item', value=100)
    
    updated = await manager.fetch('demo-resource', 'test-001')
    assert updated.name == 'Updated Item'
    assert updated.value == 100
    
    # Test Find One
    found = await manager.find_one('demo-resource', identifier='test-001')
    assert found is not None
    assert found.name == 'Updated Item'
    
    # Test Invalidate
    async with manager.transaction():
        await manager.invalidate_one('demo-resource', 'test-001')
    
    # After invalidation, the item should still exist but have _deleted timestamp
    invalidated = await manager.fetch('demo-resource', 'test-001')
    assert invalidated.deleted is not None


@pytest.mark.asyncio 
async def test_memory_driver_bulk_operations():
    """Test bulk operations like insert_many and upsert"""
    manager = MemoryAccessManager(None)
    
    # Clear any existing data
    manager.connector._MEMORY_STORE.clear()
    
    # Test Insert Many
    records = [
        manager.create('demo-resource', {'_id': f'bulk-{i}', 'name': f'Item {i}', 'value': i * 10})
        for i in range(1, 4)
    ]
    
    async with manager.transaction():
        await manager.insert_many('demo-resource', *records)
    
    # Verify all items were inserted
    for i in range(1, 4):
        item = await manager.fetch('demo-resource', f'bulk-{i}')
        assert item.name == f'Item {i}'
        assert item.value == i * 10
    
    # Test Upsert (update existing + insert new)
    async with manager.transaction():
        upsert_data = [
            {'_id': 'bulk-1', 'name': 'Updated Item 1', 'value': 999},  # Update existing
            {'_id': 'bulk-4', 'name': 'New Item 4', 'value': 40}       # Insert new
        ]
        await manager.upsert_many('demo-resource', *upsert_data)
    
    # Verify upsert results
    updated_item = await manager.fetch('demo-resource', 'bulk-1')
    assert updated_item.name == 'Updated Item 1'
    assert updated_item.value == 999
    
    new_item = await manager.fetch('demo-resource', 'bulk-4')
    assert new_item.name == 'New Item 4'
    assert new_item.value == 40


@pytest.mark.asyncio
async def test_memory_driver_query_operations():
    """Test complex query operations with memory driver"""
    manager = MemoryAccessManager(None)
    
    # Clear any existing data
    manager.connector._MEMORY_STORE.clear()
    
    # Insert test data
    test_data = [
        {'_id': 'query-1', 'name': 'Alpha', 'value': 10},
        {'_id': 'query-2', 'name': 'Beta', 'value': 20},
        {'_id': 'query-3', 'name': 'Gamma', 'value': 30},
        {'_id': 'query-4', 'name': 'Delta', 'value': 25}
    ]
    
    for data in test_data:
        record = manager.create('demo-resource', data)
        async with manager.transaction():
            await manager.insert(record)
    
    # Test Find All
    all_items = await manager.find_all('demo-resource')
    assert len(all_items) == 4
    
    # Test Query with limit/offset
    limited_items = await manager.query('demo-resource', limit=2, offset=1)
    assert len(limited_items) == 2
    
    # Test Query with where conditions
    # Note: Memory driver's where filtering is basic - it matches exact values
    matching_items = await manager.query('demo-resource', where={'name': 'Beta'})
    assert len(matching_items) == 1
    assert matching_items[0].name == 'Beta'


@pytest.mark.asyncio
async def test_memory_driver_error_handling():
    """Test error handling in memory driver"""
    manager = MemoryAccessManager(None)
    
    # Clear any existing data
    manager.connector._MEMORY_STORE.clear()
    
    # Test ItemNotFoundError for fetch (should raise)
    with pytest.raises(ItemNotFoundError):
        await manager.fetch('demo-resource', 'nonexistent-id')
    
    # Test find_one with nonexistent item (should return None)
    result = await manager.find_one('demo-resource', identifier='nonexistent-id')
    assert result is None
    
    # Test duplicate insert
    record = manager.create('demo-resource', {'_id': 'duplicate-test', 'name': 'Test'})
    async with manager.transaction():
        await manager.insert(record)
    
    # Trying to insert the same ID again should fail
    duplicate_record = manager.create('demo-resource', {'_id': 'duplicate-test', 'name': 'Duplicate'})
    with pytest.raises(ValueError, match='Item already exists'):
        async with manager.transaction():
            await manager.insert(duplicate_record)


@pytest.mark.asyncio
async def test_memory_driver_transaction_rollback():
    """Test transaction rollback functionality"""
    manager = MemoryAccessManager(None)
    
    # Clear any existing data
    manager.connector._MEMORY_STORE.clear()
    
    # Insert initial data
    initial_record = manager.create('demo-resource', {'_id': 'rollback-test', 'name': 'Initial', 'value': 1})
    async with manager.transaction():
        await manager.insert(initial_record)
    
    # Verify initial state
    initial_item = await manager.fetch('demo-resource', 'rollback-test')
    assert initial_item.value == 1
    
    # Test transaction rollback on error
    try:
        async with manager.transaction():
            await manager.update_one('demo-resource', 'rollback-test', value=999)
            # Force an error to trigger rollback
            raise ValueError("Simulated error")
    except ValueError:
        pass  # Expected error
    
    # Verify rollback - value should still be 1
    rolled_back_item = await manager.fetch('demo-resource', 'rollback-test')
    assert rolled_back_item.value == 1  # Should be unchanged due to rollback
