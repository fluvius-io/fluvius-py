import os
import pickle

from contextlib import asynccontextmanager
from fluvius.data import identifier, logger, timestamp
from fluvius.data.exceptions import ItemNotFoundError, NoItemModifiedError
from fluvius.data.query import (
    BackendQuery,
    OperatorStatement,
    process_query_statement,
    combine_query_statement,
    process_query_element,
    QueryStatement
)

from ..base import DataDriver


def query_resource(store, q: BackendQuery):
    query_stmts = tuple()

    if q.where:
        query_stmts += q.where

    if q.scope:
        query_stmts += q.scope

    if q.identifier:
        query_stmts += (process_query_element('_id.eq', q.identifier),)

    def _apply_operator(item_value, expected_value, operator, mode):
        """Apply operator logic for memory driver queries"""
        # Handle negation mode
        negate = mode == '!'
        
        # Apply the operator
        if operator == 'eq':
            result = item_value == expected_value
        elif operator == 'ne':
            result = item_value != expected_value
        elif operator == 'gt':
            result = item_value is not None and item_value > expected_value
        elif operator == 'gte':
            result = item_value is not None and item_value >= expected_value
        elif operator == 'lt':
            result = item_value is not None and item_value < expected_value
        elif operator == 'lte':
            result = item_value is not None and item_value <= expected_value
        elif operator == 'in':
            result = item_value in expected_value if expected_value else False
        elif operator == 'notin':
            result = item_value not in expected_value if expected_value else True
        elif operator == 'cs':  # contains
            result = expected_value in str(item_value) if item_value is not None else False
        elif operator == 'ilike':  # case insensitive like
            result = expected_value.lower() in str(item_value).lower() if item_value is not None else False
        else:
            # Default to equality for unknown operators
            raise ValueError(f'(memory store) Unsupported query operator: {operator}')
        
        # Apply negation if needed
        return not result if negate else result

    def _match(item):
        # Handle both dict and object items
        for qe in query_stmts:
            # Handle OperatorStatement objects
            field_name = qe.field_name

            # Get the item value
            if isinstance(item, dict):
                item_value = item.get(field_name)
            else:
                item_value = getattr(item, field_name, None)

            # Apply operator logic
            if not _apply_operator(item_value, qe.value, qe.operator, qe.mode):
                return False

        return True

    results = list(filter(_match, store.values()))

    # Apply sorting if specified
    if q.sort:
        for sort_expr in reversed(q.sort):  # Apply in reverse order for stable sorting
            field_name, _, sort_type = sort_expr.rpartition(':')
            if not field_name:
                field_name = sort_type
                sort_type = 'asc'

            reverse = sort_type == 'desc'
            try:
                def get_sort_key(x):
                    if isinstance(x, dict):
                        return x.get(field_name)
                    else:
                        return getattr(x, field_name, None)

                results.sort(key=get_sort_key, reverse=reverse)
            except (AttributeError, TypeError):
                # Handle cases where field doesn't exist or isn't sortable
                pass

    # Apply offset and limit
    start = q.offset or 0
    end = start + (q.limit or len(results))
    return results[start:end]


class InMemoryDriver(DataDriver):
    __filepath__ = None

    def __init_subclass__(cls):
        cls._MEMORY_STORE = {}

    @asynccontextmanager
    async def transaction(self, transaction_id=None):
        # Create a transaction backup for rollback capability
        backup = {}
        for resource, store in self._MEMORY_STORE.items():
            backup[resource] = store.copy()

        try:
            yield self
            self.commit()
        except Exception:
            # Rollback on any exception
            logger.warning("Rolling back memory transaction")
            self._MEMORY_STORE.clear()
            self._MEMORY_STORE.update(backup)
            raise

    @classmethod
    def _get_memory(cls, resource):
        store = cls._MEMORY_STORE
        if resource not in store:
            store[resource] = {}
        return store[resource]

    async def find(self, resource, query, meta=None):
        store = self._get_memory(resource)
        items = query_resource(store, query)

        if meta is not None:
            meta.update({
                "total": len(store),
                "limit": query.limit,
                "offset": query.offset,
                "count": len(items)
            })
        return items

    find_all = find
    query = find

    async def find_one(self, resource, query):
        store = self._get_memory(resource)
        results = query_resource(store, query)

        if not results:
            raise ItemNotFoundError(
                errcode="L3207",
                message=f"Query item not found.\n\t[RESOURCE] {resource}\n\t[QUERY   ] {query}"
            )

        return results[0]

    @classmethod
    def commit(cls):
        if cls.__filepath__ is None:
            return

        with open(cls.__filepath__, 'wb') as f:
            pickle.dump(cls._MEMORY_STORE, f)

    @classmethod
    def load_memory(cls):
        if cls.__filepath__ is None:
            return {}

        if not os.path.isfile(cls.__filepath__):
            return {}

        with open(cls.__filepath__, 'rb') as f:
            data = pickle.load(f)
            if not isinstance(data, dict):
                logger.warning('Invalid memory store data [%s]: %s', cls.__filepath__, data)
                return {}

            return data

    @classmethod
    def connect(cls, *args, **kwargs):
        if not hasattr(cls, '_MEMORY_STORE'):
            cls._MEMORY_STORE = cls.load_memory()

        return cls._MEMORY_STORE

    async def disconnect(self):
        """Disconnect and optionally save to file"""
        self.commit()

    async def flush(self):
        """Flush any pending operations (for memory driver, this is a no-op)"""
        pass

    async def update(self, resource, query, **changes):
        store = self._get_memory(resource)
        items = query_resource(store, query)

        if not items:
            raise NoItemModifiedError(
                errcode="L1206",
                message=f"No items found to update with query: {query}"
            )

        for item in items:
            # Update the item with timestamp
            if hasattr(item, 'set'):
                # Handle object items (like DataModel instances)
                updated_item = item.set(_updated=timestamp(), **changes)
                item_id = getattr(updated_item, '_id', None) or getattr(updated_item, 'id', None)
            else:
                # Handle dict items
                updated_item = item.copy()
                updated_item.update(changes)
                updated_item['_updated'] = timestamp()
                item_id = updated_item.get('_id')

            if item_id:
                store[item_id] = updated_item
            else:
                # Fallback - try to get ID from original item
                original_id = item.get('_id') if isinstance(item, dict) else getattr(item, '_id', None)
                if original_id:
                    store[original_id] = updated_item

    update_one = update

    async def update_record(self, record, **changes):
        """Update a specific record object"""
        resource = getattr(record, '__data_schema__', 'default')
        store = self._get_memory(resource)

        if record._id not in store:
            raise ItemNotFoundError(
                errcode="L3207",
                message=f"Record not found for update: {record._id}"
            )

        updated_record = record.set(_updated=timestamp(), **changes) if hasattr(record, 'set') else record
        store[record._id] = updated_record
        return updated_record

    async def remove_one(self, resource, query):
        """Remove a single item based on query"""
        store = self._get_memory(resource)
        items = query_resource(store, query)

        if not items:
            raise ItemNotFoundError(
                errcode="L3207",
                message=f"No item found to remove with query: {query}"
            )

        item = items[0]
        if hasattr(item, '_id'):
            del store[item._id]
        return item

    async def remove_record(self, resource, query):
        """Alias for remove_one for compatibility"""
        return await self.remove_one(resource, query)

    async def insert(self, resource, record_or_data):
        store = self._get_memory(resource)

        # Handle both single records and lists
        if isinstance(record_or_data, (list, tuple)):
            results = []
            for item in record_or_data:
                if hasattr(item, '_id'):
                    if item._id in store:
                        raise ValueError(f'Item already exists: {item._id}')
                    store[item._id] = item
                    results.append(item)
                else:
                    # Handle dict data
                    item_id = item.get('_id') if isinstance(item, dict) else getattr(item, '_id', None)
                    if item_id in store:
                        raise ValueError(f'Item already exists: {item_id}')
                    store[item_id] = item
                    results.append(item)
            return results
        else:
            # Single record
            record = record_or_data
            if hasattr(record, '_id'):
                if record._id in store:
                    raise ValueError(f'Item already exists: {record._id}')
                store[record._id] = record
                return record  # Return the original record, not the data
            else:
                # Handle dict data
                record_id = record.get('_id') if isinstance(record, dict) else getattr(record, '_id', None)
                if record_id in store:
                    raise ValueError(f'Item already exists: {record_id}')
                store[record_id] = record
                return record

    async def upsert(self, resource, data_list):
        """Insert or update multiple records"""
        store = self._get_memory(resource)
        results = []

        for item_data in data_list:
            if isinstance(item_data, dict):
                item_id = item_data.get('_id')
                if item_id in store:
                    # Update existing
                    existing = store[item_id]
                    if hasattr(existing, 'set'):
                        updated = existing.set(_updated=timestamp(), **item_data)
                    else:
                        updated = item_data
                    store[item_id] = updated
                    results.append(updated)
                else:
                    # Insert new
                    store[item_id] = item_data
                    results.append(item_data)
            else:
                # Handle record objects
                item_id = getattr(item_data, '_id', None)
                if item_id in store:
                    # Update existing
                    if hasattr(item_data, 'set'):
                        updated = item_data.set(_updated=timestamp())
                    else:
                        updated = item_data
                    store[item_id] = updated
                    results.append(updated)
                else:
                    # Insert new
                    store[item_id] = item_data
                    results.append(item_data)

        return results

    async def invalidate_one(self, resource, query, **updates):
        """Mark a record as deleted by setting _deleted timestamp"""
        await self.update_one(resource, query, _deleted=timestamp(), **updates)

    @classmethod
    async def native_query(cls, query, *params, unwrapper=None, **options):
        """Execute native queries (for memory driver, this is limited)"""
        # For memory driver, native queries are limited
        # This could be extended to support more complex operations
        logger.warning("Native query support is limited in memory driver: %s", query)
        return query

    def defaults(self):
        return {"_etag": identifier.UUID_GENR_BASE64(), "_created": timestamp(), "_updated": timestamp()}
