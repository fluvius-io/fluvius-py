"""Drop schema command."""

import click
import sqlalchemy as sa
import logging as logger
from sqlalchemy.schema import DropSchema
from ._common import load_connector_class, get_tables_schemas, convert_to_async_dsn, schema_exists, schema_has_tables, async_command, create_async_engine


@click.command()
@click.argument('connector_import', type=str)
@click.option('--force', is_flag=True, help='Overwrite existing data in tables')
@async_command
async def drop_schema(connector_import: str, force: bool):
    """Drop SQLAlchemy schema for a SqlaDriver connector.
    
    CONNECTOR_IMPORT: Import string to the SqlaDriver connector class
                      (e.g., 'riparius.WorkflowConnector')
    """
    try:
        # Load the connector class using shared function
        connector_class = load_connector_class(connector_import)
        tables_schemas = get_tables_schemas(connector_class)
        
        # Convert to async DSN and create engine
        async_dsn = convert_to_async_dsn(connector_class.__db_dsn__)
        engine = create_async_engine(async_dsn)
        
        async with engine.begin() as conn:
                # Check if schema exists
            # Drop all tables first using SQLAlchemy's metadata.drop_all
            if hasattr(connector_class, '__data_schema_base__'):
                base_schema = connector_class.__data_schema_base__
                
                # For PostgreSQL, we need to handle enum dependencies with CASCADE
                # Get all tables in reverse dependency order
                tables = list(reversed(base_schema.metadata.sorted_tables))
                
                for table in tables:
                    try:
                        # Drop table with CASCADE to handle enum dependencies
                        await conn.execute(sa.text(f'DROP TABLE IF EXISTS "{table.schema}"."{table.name}" CASCADE'))
                        click.echo(f"Dropped table '{table.schema}.{table.name}'")
                    except Exception as e:
                        if force:
                            click.echo(f"Warning: Failed to drop table '{table.schema}.{table.name}': {e}")
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
                
                click.echo(f"All tables and types for of connector '{connector_import}' dropped successfully.")
            
            click.echo(f"Tables schemas: {tables_schemas}")
            for schema_name in tables_schemas:
                if not await schema_exists(conn, schema_name):
                    click.echo(f"Schema '{schema_name}' does not exist.")
                    continue
            
                await conn.execute(DropSchema(schema_name, cascade=force))
                click.echo(f"Schema '{schema_name}' dropped successfully.")
        
        
        await engine.dispose()
            
    except Exception as e:
        logger.exception(f"Failed to drop schema: {e}")
        raise click.ClickException(f"Failed to drop schema: {e}") 
