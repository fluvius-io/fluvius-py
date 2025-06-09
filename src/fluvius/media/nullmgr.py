import uuid
from typing import Any

class NullMediaManager:
    """Mock MediaManager for testing without database connection"""
    
    def __init__(self, app=None):
        self._app = app
        self._entries = {}  # Store mock entries by ID
        self._filesystems = {}  # Store mock filesystems by fskey
    
    def create(self, model_name: str, data: dict = None, **kwargs) -> Any:
        """Create a mock model instance (not async, matches DataAccessManager)"""
        all_data = (data or {})
        all_data.update(kwargs)
        
        if model_name == 'MediaEntry':
            entry = type('MediaEntry', (), all_data)()
            entry._id = all_data.get('_id', str(uuid.uuid4()))
            return entry
        elif model_name == 'MediaFilesystem':
            filesystem = type('MediaFilesystem', (), all_data)()
            filesystem._id = all_data.get('_id', str(uuid.uuid4()))
            return filesystem
        else:
            # Generic mock object
            obj = type(model_name, (), all_data)()
            obj._id = all_data.get('_id', str(uuid.uuid4()))
            return obj
    
    async def insert(self, record: Any) -> Any:
        """Insert a mock record (async, matches DataAccessManager)"""
        # Store the record for later retrieval
        if hasattr(record, 'filename'):  # MediaEntry
            self._entries[record._id] = record
        elif hasattr(record, 'fskey'):  # MediaFilesystem
            self._filesystems[record.fskey] = record
            
        return record
    
    async def fetch(self, model_name: str, identifier: str) -> Any:
        """Fetch a mock model instance by ID"""
        if model_name == 'MediaEntry':
            if identifier in self._entries:
                return self._entries[identifier]
            else:
                raise ValueError(f"MediaEntry {identifier} not found")
        elif model_name == 'MediaFilesystem':
            # For MediaFilesystem, identifier could be fskey
            if identifier in self._filesystems:
                return self._filesystems[identifier]
            else:
                raise ValueError(f"MediaFilesystem {identifier} not found")
        else:
            raise ValueError(f"Mock model {model_name} not supported")
    
    async def remove(self, record: Any) -> bool:
        """Remove a mock record (matches DataAccessManager interface)"""
        if hasattr(record, 'filename'):  # MediaEntry
            if record._id in self._entries:
                del self._entries[record._id]
                return True
        elif hasattr(record, 'fskey'):  # MediaFilesystem
            if record.fskey in self._filesystems:
                del self._filesystems[record.fskey]
                return True
        return False
    
    async def query(self, model_name: str, q=None, return_meta=None, **query_params) -> list:
        """Query mock model instances with optional filtering (matches DataAccessManager)"""
        if model_name == 'MediaEntry':
            entries = list(self._entries.values())
            
            # Extract pagination parameters first
            limit = query_params.pop('limit', 100)
            offset = query_params.pop('offset', 0)
            
            # Apply filters from remaining query_params
            if query_params:
                filtered_entries = []
                for entry in entries:
                    match = True
                    for key, value in query_params.items():
                        if not hasattr(entry, key) or getattr(entry, key) != value:
                            match = False
                            break
                    if match:
                        filtered_entries.append(entry)
                entries = filtered_entries
            
            # Apply pagination
            return entries[offset:offset + limit]
        else:
            return []

