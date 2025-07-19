"""Database management commands."""

import asyncio
import click
import sqlalchemy as sa
from sqlalchemy.schema import CreateSchema, DropSchema
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from fluvius.data import SqlaDriver, logger
from fluvius.helper import load_string
from flvctl import async_command


def load_connector_class(connector_import: str) -> type:
    """Load and validate a SqlaDriver connector class.
    
    Args:
        connector_import: Import string to the SqlaDriver connector class
        
    Returns:
        The connector class
        
    Raises:
        click.ClickException: If the class is not a SqlaDriver or cannot be loaded
    """
    try:
        connector_class = load_string(connector_import)
        
        if not issubclass(connector_class, SqlaDriver):
            raise click.ClickException(f"Class {connector_class.__name__} is not a SqlaDriver")
        
        return connector_class
    except ImportError as e:
        raise click.ClickException(f"Failed to import connector: {e}")
    except AttributeError as e:
        raise click.ClickException(f"Invalid connector class: {e}")


def get_schema_name(connector_class: type) -> str:
    """Get the schema name from a connector's base schema.
    
    Args:
        connector_class: The SqlaDriver connector class
        
    Returns:
        The schema name (defaults to 'public' if not specified)
    """
    if hasattr(connector_class, '__data_schema_base__'):
        base_schema = connector_class.__data_schema_base__
        logger.info(f"base_schema: {base_schema.__table_args__}")
        if hasattr(base_schema, '__table_args__'):
            table_args = base_schema.__table_args__
            if isinstance(table_args, dict) and 'schema' in table_args:
                return table_args['schema']
    
    return 'public'


def convert_to_async_dsn(dsn: str) -> str:
    """Convert a sync DSN to async DSN."""
    if dsn.startswith('postgresql://'):
        return dsn.replace('postgresql://', 'postgresql+asyncpg://', 1)
    elif dsn.startswith('mysql://'):
        return dsn.replace('mysql://', 'mysql+aiomysql://', 1)
    elif dsn.startswith('sqlite://'):
        return dsn.replace('sqlite://', 'sqlite+aiosqlite://', 1)
    return dsn


async def schema_exists(conn, schema_name: str) -> bool:
    """Check if a schema exists in the database.
    
    Args:
        conn: The async SQLAlchemy connection
        schema_name: The schema name to check
        
    Returns:
        True if the schema exists, False otherwise
    """
    result = await conn.execute(sa.text(
        "SELECT schema_name FROM information_schema.schemata WHERE schema_name = :schema"
    ), {"schema": schema_name})
    
    return result.fetchone() is not None


async def schema_has_tables(conn, schema_name: str) -> bool:
    """Check if a schema has tables in the database.
    
    Args:
        conn: The async SQLAlchemy connection
        schema_name: The schema name to check
        
    Returns:
        True if the schema has tables, False otherwise
    """
    result = await conn.execute(sa.text(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = :schema"
    ), {"schema": schema_name})
    
    return result.fetchone() is not None


async def table_exists(conn, schema_name: str, table_name: str) -> bool:
    """Check if a table exists in the database.
    
    Args:
        conn: The async SQLAlchemy connection
        schema_name: The schema name
        table_name: The table name
        
    Returns:
        True if the table exists, False otherwise
    """
    result = await conn.execute(sa.text(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = :schema AND table_name = :table"
    ), {"schema": schema_name, "table": table_name})
    
    return result.fetchone() is not None


@click.group()
def commands():
    """Database management commands."""
    pass


@commands.command()
@click.argument('connector_import', type=str)
@click.option('--force', is_flag=True, help='Force creation even if schema exists')
@click.option('--tables-only', is_flag=True, help='Create only tables, skip schema creation')
@async_command
async def create_schema(connector_import: str, force: bool, tables_only: bool):
    """Create SQLAlchemy schema and tables for a SqlaDriver connector.
    
    CONNECTOR_IMPORT: Import string to the SqlaDriver connector class
                      (e.g., 'riparius.WorkflowConnector')
    """
    try:
        # Load the connector class using shared function
        connector_class = load_connector_class(connector_import)
        schema_name = get_schema_name(connector_class)
        
        # Convert to async DSN and create engine
        async_dsn = convert_to_async_dsn(connector_class.__db_dsn__)
        engine = create_async_engine(async_dsn)
        
        async with engine.begin() as conn:
            # Create schema if not tables_only
            if not tables_only:
                # Check if schema exists
                if await schema_exists(conn, schema_name) and not force:
                    click.echo(f"Schema '{schema_name}' already exists. Use --force to recreate.")
                    return
                
                # Create schema
                await conn.execute(CreateSchema(schema_name))
                click.echo(f"Schema '{schema_name}' created successfully.")
            
            # Create all tables defined in the connector
            if hasattr(connector_class, '__data_schema_base__'):
                base_schema = connector_class.__data_schema_base__
                
                # Use SQLAlchemy's metadata.create_all to create all tables
                await conn.run_sync(lambda sync_conn: base_schema.metadata.create_all(sync_conn, checkfirst=not force))
                click.echo(f"All tables for schema '{schema_name}' created successfully.")
            else:
                click.echo("No base schema found in connector.")
        
        await engine.dispose()
            
    except Exception as e:
        raise click.ClickException(f"Failed to create schema: {e}")


@commands.command()
@click.argument('connector_import', type=str)
@click.option('--force', is_flag=True, help='Force drop even if schema has tables')
@async_command
async def drop_schema(connector_import: str, force: bool):
    """Drop SQLAlchemy schema for a SqlaDriver connector.
    
    CONNECTOR_IMPORT: Import string to the SqlaDriver connector class
                      (e.g., 'riparius.WorkflowConnector')
    """
    try:
        # Load the connector class using shared function
        connector_class = load_connector_class(connector_import)
        schema_name = get_schema_name(connector_class)
        
        # Convert to async DSN and create engine
        async_dsn = convert_to_async_dsn(connector_class.__db_dsn__)
        engine = create_async_engine(async_dsn)
        
        async with engine.begin() as conn:
            # Check if schema exists
            if not force:
                if not await schema_exists(conn, schema_name):
                    click.echo(f"Schema '{schema_name}' does not exist.")
                    return
                
                # Check if schema has tables (if not forcing)
                if await schema_has_tables(conn, schema_name):
                    click.echo(f"Schema '{schema_name}' contains tables. Use --force to drop anyway.")
                    return
            
            # Drop all tables first using SQLAlchemy's metadata.drop_all
            if hasattr(connector_class, '__data_schema_base__'):
                base_schema = connector_class.__data_schema_base__
                
                # For PostgreSQL, we need to handle enum dependencies with CASCADE
                # Get all tables in reverse dependency order
                tables = list(reversed(base_schema.metadata.sorted_tables))
                
                for table in tables:
                    try:
                        # Drop table with CASCADE to handle enum dependencies
                        await conn.execute(sa.text(f'DROP TABLE IF EXISTS "{schema_name}"."{table.name}" CASCADE'))
                        click.echo(f"Dropped table '{schema_name}.{table.name}'")
                    except Exception as e:
                        if force:
                            click.echo(f"Warning: Failed to drop table '{schema_name}.{table.name}': {e}")
                        else:
                            raise
                
                # Drop any remaining custom types (enums) that might not have been dropped by CASCADE
                # Get all enum types from the metadata by inspecting table columns
                enum_types = set()
                for table in base_schema.metadata.tables.values():
                    for column in table.columns:
                        if hasattr(column.type, 'name') and column.type.name:
                            enum_types.add(column.type.name)
                
                for enum_name in enum_types:
                    try:
                        # Drop enum at database level (not schema-specific in PostgreSQL)
                        await conn.execute(sa.text(f'DROP TYPE IF EXISTS "{enum_name}" CASCADE'))
                        click.echo(f"Dropped enum type '{enum_name}'")
                    except Exception as e:
                        if force:
                            click.echo(f"Warning: Failed to drop enum type '{enum_name}': {e}")
                
                click.echo(f"All tables and types for schema '{schema_name}' dropped successfully.")
            
            # Drop schema
            await conn.execute(DropSchema(schema_name, cascade=force))
            click.echo(f"Schema '{schema_name}' dropped successfully.")
        
        await engine.dispose()
            
    except Exception as e:
        raise click.ClickException(f"Failed to drop schema: {e}") 