
import click
import sqlalchemy as sa
from sqlalchemy.schema import CreateSchema, DropSchema
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from fluvius.data import SqlaDriver, logger
from fluvius.helper import load_string
from .. import async_command


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


def get_tables_schemas(connector_class: type) -> str:
    """Get the schema names from a connector's base schema.
    
    Args:
        connector_class: The SqlaDriver connector class
        
    Returns:
        The schema names
    """
    if hasattr(connector_class, '__data_schema_base__'):
        base_schema = connector_class.__data_schema_base__
        schemas = {
            t.schema for t in base_schema.metadata.tables.values() if t.schema is not None
        }        
    
    return schemas


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



__all__ = [
    'async_command',
    'create_async_engine',
    'load_connector_class', 
    'get_schema_name', 
    'convert_to_async_dsn', 
    'schema_exists', 
    'schema_has_tables'
]
