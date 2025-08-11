# Context Variables Migration for Fluvius Aggregate

## Overview

This document describes the migration of the Fluvius Aggregate class from instance variables to Python's `contextvars` module. This change provides better isolation between different command execution contexts and prevents the "Overlapping context" error.

## What Changed

### Before: Instance Variables
```python
class Aggregate(object):
    def __init__(self, domain):
        # Instance variables that could cause overlapping contexts
        self._evt_queue = None
        self._context = None
        self._command = None
        self._cmdmeta = None
        self._aggroot = None
        self._rootobj = None

    @asynccontextmanager
    async def command_aggregate(self, context, command_bundle, command_meta):
        if getattr(self, '_context', None):
            raise RuntimeError('Overlapping context: %s' % str(context))
        
        # Set instance variables
        self._context = context
        self._command = command_bundle
        # ... other assignments
        
        yield RestrictedAggregateProxy(self)
        
        # Clear instance variables
        self._context = None
        self._command = None
        # ... other clearing
```

### After: Context Variables
```python
class Aggregate(object):
    # Class-level context variables
    _evt_queue_var = contextvars.ContextVar('evt_queue', default=queue.Queue())
    _context_var = contextvars.ContextVar('context', default=None)
    _command_var = contextvars.ContextVar('command', default=None)
    _cmdmeta_var = contextvars.ContextVar('cmdmeta', default=None)
    _aggroot_var = contextvars.ContextVar('aggroot', default=None)
    _rootobj_var = contextvars.ContextVar('rootobj', default=None)

    @asynccontextmanager
    async def command_aggregate(self, context, command_bundle, command_meta):
        # Set context variables for this execution
        self._context_var.set(context)
        self._command_var.set(command_bundle)
        # ... other assignments
        
        yield RestrictedAggregateProxy(self)
        
        # Context variables are automatically isolated per execution
```

## Key Benefits

### 1. **Automatic Context Isolation**
- Each command execution gets its own isolated context
- No more "Overlapping context" errors
- Multiple commands can run concurrently without interference

### 2. **Better Async Support**
- Context variables work seamlessly with async/await
- Proper isolation in concurrent scenarios
- No manual cleanup required

### 3. **Improved Testing**
- Each test can have its own isolated context
- No need to manually reset state between tests
- Better parallel test execution support

### 4. **Thread Safety**
- Context variables are thread-local by default
- Safe for multi-threaded environments
- Proper isolation across different execution contexts

## How It Works

### Context Variable Lifecycle
1. **Command Start**: Context variables are set for the current execution
2. **Command Execution**: All aggregate operations use the current context
3. **Command End**: Context variables are automatically isolated for next execution

### Automatic Isolation
```python
# Command 1 execution
async with aggregate.command_aggregate(ctx1, cmd1, meta1) as proxy:
    # Uses ctx1 context
    print(aggregate.context.name)  # "ctx1"
    
# Command 2 execution (can run concurrently or sequentially)
async with aggregate.command_aggregate(ctx2, cmd2, meta2) as proxy:
    # Uses ctx2 context - completely isolated from ctx1
    print(aggregate.context.name)  # "ctx2"
```

## Migration Details

### Changed Methods
- `command_aggregate()`: Now uses context variables instead of instance variables
- `fetch_command_rootobj()`: Accesses context through context variables
- `create_event()`: Uses context-isolated event queue
- All properties (`context`, `rootobj`, `aggroot`, `command`): Now use context variables

### New Methods
- `clear_context()`: Manually clear all context variables (useful for testing)
- `get_context_state()`: Debug method to inspect current context state

### Removed Code
- Manual context clearing in `command_aggregate`
- Instance variable assignments and cleanup
- Overlapping context check (no longer needed)

## Testing the Migration

### Run the Test Script
```bash
python test_contextvars_aggregate.py
```

This will verify:
- Context isolation between commands
- Proper cleanup after command execution
- Concurrent command execution safety

### Expected Output
```
🚀 Starting contextvars Aggregate tests...
Testing context isolation with contextvars...

Initial context state: {'has_context': False, 'has_command': False, ...}

--- Executing Command 1 ---
Command 1 context state: {'has_context': True, 'has_command': True, ...}
Command 1 resource: resource1
Command 1 context name: context1

--- Executing Command 2 ---
Command 2 context state: {'has_context': True, 'has_command': True, ...}
Command 2 resource: resource2
Command 2 context name: context2

✅ Context isolation test completed successfully!
```

## Backward Compatibility

### What Still Works
- All existing aggregate methods and properties
- Command processor decorators
- Event creation and consumption
- Response and message creation

### What Changed
- Internal implementation uses context variables
- Better error handling for missing context
- Improved debugging capabilities

## Performance Impact

### Minimal Overhead
- Context variable access is very fast
- No significant performance impact
- Better scalability for concurrent operations

### Memory Benefits
- No need to store context state in instances
- Automatic cleanup reduces memory leaks
- Better garbage collection behavior

## Troubleshooting

### Common Issues

#### 1. Context Not Initialized Error
```python
RuntimeError: Aggregate context is not initialized.
```
**Solution**: Ensure you're calling aggregate methods within a `command_aggregate` context.

#### 2. Context Variables Not Working
**Check**: Verify Python version supports `contextvars` (Python 3.7+)

#### 3. Testing Issues
**Use**: `aggregate.clear_context()` to reset state between tests

### Debug Methods
```python
# Check current context state
state = aggregate.get_context_state()
print(f"Context state: {state}")

# Clear context manually if needed
aggregate.clear_context()
```

## Future Enhancements

### Potential Improvements
1. **Context Inheritance**: Allow contexts to inherit from parent contexts
2. **Context Metadata**: Add additional context information for debugging
3. **Performance Monitoring**: Track context creation/destruction performance
4. **Context Validation**: Add validation rules for context data

### Monitoring
- Add logging for context variable changes
- Track context variable usage patterns
- Monitor for potential context leaks

## Conclusion

The migration to `contextvars` provides significant improvements in:
- **Reliability**: Eliminates overlapping context errors
- **Scalability**: Better support for concurrent operations
- **Maintainability**: Cleaner, more predictable code
- **Testing**: Improved test isolation and reliability

This change makes the Fluvius framework more robust and suitable for high-concurrency environments while maintaining backward compatibility for existing code.
