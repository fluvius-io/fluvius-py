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
- **Implementation:** Used individual table creation:
  ```python
  await conn.run_sync(CompanySchema.__table__.create)
  await conn.run_sync(CompanyMemberSchema.__table__.create)
  await conn.run_sync(CompanySystemRoleSchema.__table__.create)
  ```

### 3. Query Syntax Understanding
- **Discovery:** Fluvius query syntax uses specific operators:
  - `!or` = negated OR (`NOT(condition1 OR condition2)`)
  - `.or` = normal OR (`condition1 OR condition2`)
  - `!ne` = negated not-equal (becomes equal)
- **Test Query Analysis:**
  - `{"!or": [{"business_name!ne": "ABC1"}, {"business_name": "DEF3"}]}` 
  - Translates to: `NOT(business_name = "ABC1" OR business_name = "DEF3")`
  - Returns records that are neither "ABC1" nor "DEF3"

### 4. VS Code Configuration
- **Problem:** Linter errors due to incorrect Python interpreter and import resolution
- **Solution:** Created `.vscode/settings.json` with:
  - Python interpreter: `/Users/lexhung/.virtualenvs/pydarts/bin/python3`
  - Extra paths for import resolution: `./src`, `./tests/_lib`, `./examples`
  - Environment variables matching Justfile configuration
  - PYTHONPATH: `./lib:./src:./tests/_lib:./examples`

### 5. Test Organization Analysis ⚠️ NEEDS ATTENTION
- **Problem:** Redundant and confusing test code organization
- **Current Issues:**
  - `sample_data_schema.py` exists in both `tests/_lib/` and `examples/sample_data_model/`
  - Unclear separation between test fixtures, examples, and actual tests
  - Import confusion due to scattered test utilities
- **Impact:** Makes tests harder to maintain and understand

## Files Modified

1. **`tests/fluvius_query/test_query.py`**
   - Added `setup_database()` function
   - Fixed test assertions to match actual query behavior
   - Added detailed comments explaining query logic

2. **`.vscode/settings.json`** (new file)
   - Configured Python interpreter path
   - Set up import resolution paths
   - Added environment variables
   - Configured linting and formatting tools

## Test Results

All tests now pass successfully:
- `test_query_1`: ✅ Complex query operations with negation and OR logic
- `test_query_2`: ✅ ObjectDomainQueryManager (empty result as expected)
- `test_query_items`: ✅ Placeholder test (TODO)
- `test_query_endpoints`: ✅ Placeholder test (TODO)

## Commands Used

```bash
# Run fluvius_query tests
just test fluvius_query

# Run all tests
just test "*"
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
├── _lib/
│   ├── sample_data_model.py    # Test utilities
│   ├── sample_data_schema.py   # 🔄 DUPLICATE
│   ├── cqrs_fixtures.py
│   └── datamap_helper.py
├── fluvius_*/                  # Individual test modules
└── ...

examples/
├── sample_data_model/
│   ├── sample_data_schema.py   # 🔄 DUPLICATE
│   └── __init__.py
├── object_domain/              # Used by tests
└── ...
```

## Next Steps / TODOs

1. **🚨 PRIORITY: Reorganize test structure** (see detailed plan below)
2. Implement `test_query_items()` function
3. Implement `test_query_endpoints()` function  
4. Consider adding more complex query test cases
5. Verify VS Code configuration resolves all linter errors

## Environment Details

- **Python:** `/Users/lexhung/.virtualenvs/pydarts/bin/python3`
- **Workspace:** `/private/abx/rfx-platform/lib/fluvius`
- **Test Command:** `just test fluvius_query`
- **Config File:** `config.ini` 