# Test Organization Improvement Plan

## Current Problems

### 1. **Duplication**
- `sample_data_schema.py` exists in both `tests/_lib/` and `examples/sample_data_model/`
- Unclear which version tests should import
- Maintenance nightmare when schemas change

### 2. **Confused Boundaries**
- `examples/` contains code that tests depend on
- Tests import from examples, blurring the line between test utilities and documentation
- Examples should be self-contained demonstrations, not dependencies

### 3. **Import Complexity**
- PYTHONPATH includes multiple directories: `./lib:./src:./tests/_lib:./examples`
- Tests have complex import dependencies
- Hard to understand what's a test utility vs example vs production code

## Recommended Structure

### Option A: Centralized Test Utilities (Recommended)

```
tests/
├── conftest.py              # Global pytest fixtures
├── fixtures/                # 🆕 Centralized test utilities
│   ├── __init__.py
│   ├── data_models.py       # Sample data models for testing
│   ├── data_schemas.py      # Sample database schemas
│   ├── domain_fixtures.py   # Domain-specific test objects
│   ├── cqrs_fixtures.py     # CQRS test utilities
│   └── factories.py         # Test data factories
├── unit/                    # 🆕 Unit tests
│   ├── test_query.py
│   ├── test_data.py
│   └── ...
├── integration/             # 🆕 Integration tests
│   ├── test_fastapi.py
│   ├── test_worker.py
│   └── ...
└── e2e/                     # 🆕 End-to-end tests
    └── ...

examples/                    # 🔄 Pure examples (no test dependencies)
├── basic_usage/
├── domain_modeling/
├── query_examples/
└── ...

src/fluvius/                 # Production code
└── ...
```

### Option B: Hybrid Approach (Alternative)

Keep current structure but eliminate duplication:

```
tests/
├── fixtures/                # 🆕 Rename _lib to fixtures
│   ├── shared_models.py     # 🔄 Rename from sample_data_model.py
│   ├── shared_schemas.py    # 🔄 Rename from sample_data_schema.py
│   └── ...
├── fluvius_query/           # Keep existing test modules
├── fluvius_data/
└── ...

examples/                    # 🔄 Self-contained examples only
├── sample_app/              # Complete example apps
├── tutorials/               # Step-by-step guides
└── ...
```

## Migration Plan

### Phase 1: Eliminate Duplication ⚡ (Quick Win)

1. **Choose the authoritative source:**
   ```bash
   # Keep tests/_lib/sample_data_schema.py as source of truth
   # Remove examples/sample_data_model/sample_data_schema.py
   ```

2. **Update imports in tests:**
   ```python
   # Change from:
   from object_domain.query import ObjectDomainQueryManager
   
   # To:
   from tests.fixtures.domain_fixtures import ObjectDomainQueryManager
   ```

3. **Update PYTHONPATH:**
   ```bash
   # Simplify from: ./lib:./src:./tests/_lib:./examples
   # To: ./src:./tests
   ```

### Phase 2: Reorganize Structure 📁 (Medium term)

1. **Create `tests/fixtures/` directory**
2. **Move and rename utilities:**
   - `tests/_lib/sample_data_model.py` → `tests/fixtures/data_models.py`
   - `tests/_lib/sample_data_schema.py` → `tests/fixtures/data_schemas.py`
   - `tests/_lib/cqrs_fixtures.py` → `tests/fixtures/cqrs_fixtures.py`

3. **Update all test imports**
4. **Create self-contained examples**

### Phase 3: Enhance Testing 🚀 (Long term)

1. **Add pytest fixtures in `conftest.py`**
2. **Create test data factories**
3. **Organize tests by type (unit/integration/e2e)**

## Implementation Script

```bash
#!/bin/bash
# Phase 1: Quick duplication fix

echo "Phase 1: Eliminating duplication..."

# Remove duplicate schema file
rm examples/sample_data_model/sample_data_schema.py

# Update examples to be self-contained
# (Move object_domain to tests/fixtures/)

# Update VS Code settings
# Remove ./examples from PYTHONPATH

echo "✅ Phase 1 complete"
```

## Benefits of This Approach

### ✅ **Clearer Separation of Concerns**
- Tests have their own utilities in `tests/fixtures/`
- Examples are pure documentation/demos
- Production code in `src/`

### ✅ **Easier Maintenance**
- Single source of truth for test utilities
- Clear import paths
- No duplication

### ✅ **Better Developer Experience**
- Simplified PYTHONPATH
- Predictable import structure
- Self-contained examples

### ✅ **Improved CI/CD**
- Faster test discovery
- Cleaner dependency tree
- Better test isolation

## Migration Effort

| Phase | Effort | Risk | Impact |
|-------|--------|------|--------|
| Phase 1 | 2-4 hours | Low | High |
| Phase 2 | 1-2 days | Medium | High |
| Phase 3 | 3-5 days | Low | Medium |

## Recommendation

**Start with Phase 1** - it's a quick win that eliminates the most confusing aspects of the current structure with minimal risk.

The current test organization is functional but confusing. A phased approach allows us to improve it incrementally without breaking existing functionality. 