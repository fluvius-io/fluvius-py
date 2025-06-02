# AI Context - Quick Start Guide

> 👋 **New AI Session?** Read this first for immediate context!

## Current Project: Fluvius Library
- **Location:** `/private/abx/rfx-platform/lib/fluvius` 
- **Python:** `/Users/lexhung/.virtualenvs/pydarts/bin/python3`
- **Type:** Python library for query management, data access, and domain modeling

## Essential Commands
```bash
# Test specific module
just test fluvius_query

# Test everything  
just test "*"

# View available commands
just --list
```

## Recent Work (Always Check `docs/notes.ai/` for Latest)
- ✅ Fixed fluvius.query tests (2024-12-20)
- ✅ Configured VS Code Python environment
- ✅ Database schema setup for SQLite tests

## Key Files to Know
- `tests/fluvius_query/test_query.py` - Main query tests (recently fixed)
- `.vscode/settings.json` - Python environment config
- `Justfile` - Task runner (like Makefile)
- `tests/_lib/sample_data_model.py` - Test data models
- `src/fluvius/query/` - Query system source code

## Environment Setup
- Virtual env: `/Users/lexhung/.virtualenvs/pydarts/`
- PYTHONPATH: `./lib:./src:./tests/_lib:./examples`
- Config: `config.ini`

## Common Issues & Solutions
1. **Import errors** → Check VS Code Python interpreter setting
2. **Test database errors** → Ensure SQLite tables created individually
3. **Query syntax confusion** → `!or` = negated OR, `.or` = normal OR

## Next Time: Start Here
1. Ask me to read the latest file in `docs/notes.ai/`
2. Mention what you want to work on
3. I'll catch up quickly and we can continue! 