# Fluvius Command Line Tool (flvctl)

A command line interface for managing Fluvius applications and databases.

## Installation

The tool is part of the Fluvius package and can be run directly:

```bash
# Run as module
python -m fluvius.cmd.flvctl

# Or if installed as a script
flvctl
```

## Usage

### Database Management

#### Create Schema and Tables for a Connector

```bash
# Create schema and all tables for a workflow connector
flvctl db create-schema fluvius.cmd.flvctl.db.connectors.WorkflowConnector

# Force recreate if schema/tables exist
flvctl db create-schema fluvius.cmd.flvctl.db.connectors.WorkflowConnector --force

# Create only tables (skip schema creation)
flvctl db create-schema fluvius.cmd.flvctl.db.connectors.WorkflowConnector --tables-only
```

#### Drop Schema for a Connector

```bash
# Drop schema for a workflow connector
flvctl db drop-connector-schema fluvius.cmd.flvctl.db.connectors.WorkflowConnector

# Force drop even if schema has tables
flvctl db drop-connector-schema fluvius.cmd.flvctl.db.connectors.WorkflowConnector --force
```

### Runtime Management

#### Start Runtime

```bash
# Start with default config
flvctl run start

# Start with custom config
flvctl run start --config /path/to/config.yaml
```

#### Stop Runtime

```bash
flvctl run stop
```

#### Check Status

```bash
# Basic status
flvctl run status

# Detailed status
flvctl run status --status
```

## Command Structure

```
flvctl
├── db
│   ├── create-schema
│   └── drop-connector-schema
└── run
    ├── start
    ├── stop
    └── status
```

## Creating Custom Connectors

To use the database commands with your own connectors:

1. Create a connector class that inherits from `SqlaDriver`
2. Set the `__db_dsn__` attribute
3. Create a base schema class that inherits from your connector's `__data_schema_base__` and `DomainSchema`
4. Set `__table_args__ = {'schema': 'your_schema_name'}` in the base schema
5. Define your table models as classes that inherit from the base schema
6. Use the import string to your connector class with the commands

Example:
```python
from fluvius.data import SqlaDriver, DomainSchema
import sqlalchemy as sa

class MyConnector(SqlaDriver):
    __db_dsn__ = "postgresql://user:pass@localhost:5432/mydb"

class MyBaseSchema(MyConnector.__data_schema_base__, DomainSchema):
    __abstract__ = True
    __table_args__ = {'schema': 'myapp'}

class UserModel(MyBaseSchema):
    __tablename__ = "users"
    name = sa.Column(sa.String(255), nullable=False)
    email = sa.Column(sa.String(255), nullable=False)
```

Then use:
```bash
# This will create the 'myapp' schema and the 'users' table
flvctl db create-schema mymodule.MyConnector
```

## Command Options

### create-schema
- `--force`: Force recreation of schema and tables even if they exist
- `--tables-only`: Create only tables, skip schema creation (useful if schema already exists) 
