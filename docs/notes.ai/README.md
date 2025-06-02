# AI Session Notes System

This directory contains detailed notes from AI pair programming sessions to maintain continuity across sessions.

## How to Use This System

### For New AI Sessions:
1. **Start by reading the most recent notes** to understand current state
2. **Reference specific previous sessions** when working on related topics
3. **Always update or create new notes** for the current session

### File Naming Convention:
- Format: `YYYY-MM-DD-brief-subject-description.md`
- Example: `2024-12-20-fluvius-query-test-review-and-vscode-setup.md`

### Quick Context Template:
When starting a new session, tell the AI:

```
Please read docs/notes.ai/[latest-file].md to understand what we worked on recently. 
I want to continue working on [specific topic/issue].
```

## Session Index

| Date | Subject | Key Files Modified | Status |
|------|---------|-------------------|---------|
| 2024-12-20 | Fluvius.query Test Review and VS Code Setup | `tests/fluvius_query/test_query.py`, `.vscode/settings.json`, test organization | ✅ Complete |

## Current Project State

### Working Systems:
- ✅ fluvius.query tests (`just test fluvius_query`)
- ✅ VS Code Python environment configuration
- ✅ Database schema setup for tests
- ✅ **NEW:** Simplified test organization (Phase 1 complete)

### Recent Improvements (2024-12-20):
- ✅ Eliminated duplicate `sample_data_schema.py` files
- ✅ Moved `object_domain` from examples to `tests/_lib`
- ✅ Simplified PYTHONPATH: `./src:./tests/_lib` (removed examples)
- ✅ Updated VS Code and Justfile configurations

### Active TODOs:
- [ ] Implement `test_query_items()` function
- [ ] Implement `test_query_endpoints()` function
- [ ] Add more complex query test cases
- [ ] Consider Phase 2 of test reorganization (rename `_lib` to `fixtures`)

### Key Commands:
```bash
# Test specific module
just test fluvius_query

# Test all modules  
just test "*"

# Python environment
/Users/lexhung/.virtualenvs/pydarts/bin/python3
```

### Important Paths:
- Python interpreter: `/Users/lexhung/.virtualenvs/pydarts/bin/python3`
- Workspace: `/private/abx/rfx-platform/lib/fluvius`
- Test utilities: `./tests/_lib` (single source of truth)
- Source: `./src` 