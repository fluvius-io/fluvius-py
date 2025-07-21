"""Create schema command."""

import click
from sqlalchemy.schema import CreateSchema

from ._common import load_connector_class, get_schema_name, convert_to_async_dsn, schema_exists, async_command, create_async_engine


@click.command()
@click.argument('connector_import', type=str)
@click.option('--force', is_flag=True, help='Overwrite existing data in tables')
@click.option('--tables-only', is_flag=True, help='Create only tables, no schema')
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