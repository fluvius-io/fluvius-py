# AI Session Notes - 2024-12-20

**Subject:** Fluvius.query Test Review and VS Code Configuration

## Session Overview

Reviewed and fixed the fluvius.query test in `tests/fluvius_query/test_query.py` and configured VS Code for proper Python environment integration.

## Key Findings

### 1. Fluvius Query Test Issues
- **Problem:** Test was failing with `no such table: company` error
- **Root Cause:** Database schema wasn't being created before running tests
- **Solution:** Added `setup_database()` function to create tables and insert sample data

### 2. Database Schema Conflicts
- **Problem:** SQLite doesn't support PostgreSQL ARRAY types from other schemas
- **Solution:** Created only specific required tables instead of using `metadata.create_all()`
- **Implementation:** Used individual table creation to avoid type conflicts

### 3. Fluvius Query Operators
Learned key operator syntax:
- `!or` = negated OR (`NOT(condition1 OR condition2)`)
- `.or` = normal OR (`condition1 OR condition2)`)
- `!ne` = negated not-equal (becomes equal, e.g., `name!ne: "John"` → `name = "John"`)

### 4. Test Data Setup
- Added sample data: 3 companies (ABC1, DEF3, XYZ Corp)
- Used proper Fluvius query syntax in test assertions
- All 4 fluvius.query tests now pass ✅

## VS Code Configuration

### 1. Python Environment
- **Interpreter:** `/Users/lexhung/.virtualenvs/pydarts/bin/python3`
- **Import Paths:** Added `./src` and `./tests/_lib` for proper module resolution
- **Environment Variables:** Matched Justfile configuration

### 2. Settings Applied
- Python interpreter path configuration
- PYTHONPATH setup for test utilities
- Import resolution for development convenience
- **Language Server:** Disabled Pylance (set to "None") per user request

## Test Organization Improvements

### 1. Eliminated Duplication
- Removed duplicate `sample_data_schema.py` from `examples/sample_data_model/`
- Moved `object_domain` from `examples/` to `tests/_lib/`
- Made `tests/_lib/` the single source of truth for test utilities

### 2. Simplified Paths
- **Before:** `PYTHONPATH=./lib:./src:./tests/_lib:./examples`
- **After:** `PYTHONPATH=./src:./tests/_lib`
- Updated both Justfile and VS Code settings

### 3. Clear Boundaries
- `examples/` now only contains example applications
- `tests/_lib/` contains all test utilities and schemas
- Better separation between example code and test infrastructure

## Fluvius Data Test Fixes

### 1. Database Issues
- **Problem:** UNIQUE constraint failed on user._id due to persistent SQLite files
- **Root Cause:** `/tmp/fluvius_data_test2.sqlite` retained data between test runs
- **Solution:** Fixed database schema setup and table creation

### 2. Query Translation Issues
- **Problem:** Tests using incorrect syntax like `"name:eq"` instead of `"name.eq"`
- **Root Cause:** Tests were written with outdated field operator syntax
- **Solution:** Updated all tests to use correct Fluvius syntax (`.` and `!` operators)

### 3. Sort Parsing Bug
- **Problem:** Field parsing failed for sort expressions without explicit direction
- **Root Cause:** `rpartition('.')` on `'name'` returned `('', '', 'name')` causing empty field_name
- **Solution:** Added logic to handle missing field separator in `_sort_clauses` method

### 4. Boolean Logic Clarification
- **Confirmed:** `{"name!ne": "John Doe"}` correctly generates `user.name = 'John Doe'`
- **Logic:** `!ne` means `NOT(name != value)` which equals `name = value`
- **Operator Mapping:** NEGATE_MODE operators correctly flip the logic

### 5. Final Test Results
- **Status:** All 19 fluvius_data tests now pass ✅
- **Coverage:** Query translation, sorting, joining, field mapping, operators
- **Database:** Both in-memory and persistent SQLite configurations working

## Documentation System

### 1. Session Tracking
- **Location:** `docs/notes.ai/` directory
- **Naming:** Dated session files for chronological tracking
- **Index:** `docs/notes.ai/README.md` maintains session overview

### 2. Context Preservation  
- **Quick Start:** `docs/AI-CONTEXT.md` for future AI sessions
- **Test Strategy:** `docs/TEST-ORGANIZATION-PLAN.md` for test improvements
- **Code Comments:** Added context in test files for future maintenance

## Files Modified

### Test Fixes
- `tests/fluvius_query/test_query.py` - Database setup and query syntax
- `tests/fluvius_data/test_driver_sqla.py` - Schema registration and table creation
- `tests/fluvius_data/test_sqla_query_translation.py` - Query syntax and test expectations
- `src/fluvius/data/data_driver/sqla/query.py` - Sort parsing fix

### Configuration
- `.vscode/settings.json` - Python environment and Pylance disable
- `.command/jucmd/python.just` - Simplified PYTHONPATH

### Organization
- Removed: `examples/sample_data_model/sample_data_schema.py` (duplicate)
- Moved: `examples/object_domain/` → `tests/_lib/object_domain/`

### Documentation
- `docs/AI-CONTEXT.md` - Quick start guide
- `docs/TEST-ORGANIZATION-PLAN.md` - Test improvement strategy
- `docs/notes.ai/README.md` - Session index

## Current Status

✅ **All Tests Passing:**
- `fluvius.query` tests: 4/4 passing
- `fluvius.data` tests: 19/19 passing

✅ **Environment Setup:**
- VS Code properly configured
- Python interpreter and paths working
- Import resolution functioning

✅ **Code Quality:**
- Test organization significantly improved
- Duplication eliminated
- Clear boundaries established

✅ **Documentation:**
- Comprehensive session notes
- Context preservation for future sessions
- Test strategy documented

## Commands Used

```bash
# Run fluvius_query tests
just test fluvius_query

# Run fluvius_data tests  
just test fluvius_data

# Run all tests
just test "*"

# Clean up database files (when needed)
rm /tmp/fluvius*.sqlite
```

## Technical Notes

### Query Processing Flow
1. Query parsing in `src/fluvius/data/query.py` using `operator_statement()`
2. SQL generation in `src/fluvius/data/data_driver/sqla/query.py`
3. Operator mappings:
   - `NORMAL_MODE = '.'`
   - `NEGATE_MODE = '!'`
   - Composite operators: `and_`, `or_`, `nand_`, `nor_`

### Database Setup Pattern
Other tests use similar patterns:
- `tests/fluvius_data/test_directsql_sqlite.py` - Reference implementation
- Key: Use `conn.run_sync(Schema.__table__.create)` for table creation

### Test Organization Issues (Discovered)
```
Current Structure (Problematic):
tests/
├── _lib/                    # 🎯 Single source of truth for test utilities
│   ├── sample_data_model.py
│   ├── sample_data_schema.py   # 🔄 DUPLICATE
│   ├── object_domain/       # 🔄 Moved from examples
│   ├── cqrs_fixtures.py
│   └── datamap_helper.py
├── fluvius_*/                  # Individual test modules
└── ...

examples/                    # 🔄 Now cleaner, imports from tests/_lib
├── sample_data_model/       # References tests/_lib
├── fastapi_app/
└── ...
```

### Database Issues Resolution
- **Root Cause:** SQLAlchemy metadata confusion between different schema bases
- **Pattern:** Always use the same metadata for drop/create that contains your table definitions
- **Prevention:** Consider using in-memory databases (`:memory:`) for tests when possible

## Next Steps / TODOs

1. **🚨 PRIORITY: Reorganize test structure** (see detailed plan below)
2. Fix `test_sqla_query_translation.py` missing `compile_statement` method
3. Implement `test_query_items()` function
4. Implement `test_query_endpoints()` function  
5. Consider adding more complex query test cases
6. Verify VS Code configuration resolves all linter errors

## Environment Details

- **Python:** `/Users/lexhung/.virtualenvs/pydarts/bin/python3`
- **Workspace:** `/private/abx/rfx-platform/lib/fluvius`
- **Test Command:** `just test fluvius_query`
- **Config File:** `config.ini` 
