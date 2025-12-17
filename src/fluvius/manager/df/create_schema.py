"""Create DForm element schema tables command."""

import click
from sqlalchemy.schema import CreateSchema
from sqlalchemy.ext.asyncio import create_async_engine

from ..db.base import convert_to_async_dsn, schema_exists, async_command
from ..helper import import_modules


@click.command("create-schema")
@click.option('--force', is_flag=True, help='Recreate tables even if they exist')
@click.option('--repositories', '-r', type=str, multiple=True,
              help='Element repository module to import before creating schema')
@async_command
async def create_schema(force: bool, repositories: tuple[str, ...]):
    """Create all DForm element schema tables if they don't exist.
    
    This command creates:
    - The form definition schema and tables (templates, forms, elements)
    - The element data schema and tables (element instances)
    - All registered ElementModel schema tables
    
    Use --repositories to import element definition modules before creating
    the schema. This ensures all ElementModel subclasses are registered.
    
    Example:
        fluvius dform create-schema
        fluvius dform create-schema --force
        fluvius dform create-schema -r myapp.elements
        fluvius dform create-schema -r myapp.elements.text -r myapp.elements.number
        fluvius dform create-schema --repositories myapp.elements.text myapp.elements.number
    """
    from fluvius.dform.schema import FormConnector
    from fluvius.dform.element import ElementModelRegistry, ElementDataManager
    from fluvius.dform import config
    
    try:
        click.echo("=" * 60)
        click.echo("DForm Schema Creation")
        click.echo("=" * 60)
        
        # Import element repositories if specified
        import_modules(repositories or config.DFORM_REPOSITORIES)
        
        # Get DSN and create async engine
        dsn = config.DB_DSN
        async_dsn = convert_to_async_dsn(dsn)
        engine = create_async_engine(async_dsn)
        
        click.echo(f"\nConnecting to database...")
        
        async with engine.begin() as conn:
            # Create schemas if they don't exist
            click.echo(f"\nCreating database schemas...")
            for schema_name in [config.DEFINITION_DB_SCHEMA, config.DFORM_DATA_DB_SCHEMA]:
                if not await schema_exists(conn, schema_name):
                    await conn.execute(CreateSchema(schema_name))
                    click.echo(f"  ✓ Created schema: {schema_name}")
                else:
                    click.echo(f"  • Schema already exists: {schema_name}")
            
            # Create form definition tables
            click.echo(f"\nCreating form definition tables...")
            form_metadata = FormConnector.pgmetadata()
            await conn.run_sync(
                lambda sync_conn: form_metadata.create_all(sync_conn, checkfirst=not force)
            )
            click.echo(f"  ✓ Form definition tables created")
            
            # Create element data tables from ElementDataManager
            click.echo(f"\nCreating element data tables...")
            element_metadata = ElementDataManager().connector.pgmetadata()
            await conn.run_sync(
                lambda sync_conn: element_metadata.create_all(sync_conn, checkfirst=not force)
            )
            click.echo(f"  ✓ Element data tables created")
            
            # Show registered element types
            element_types = list[str](ElementModelRegistry.keys())
            if element_types:
                click.echo(f"\nRegistered element types ({len(element_types)}):")
                for key in element_types:
                    elem_cls = ElementModelRegistry.get(key)
                    table_name = elem_cls.Meta.table_name
                    click.echo(f"  • {key} -> {config.DFORM_DATA_DB_SCHEMA}.{table_name}")
            else:
                click.echo(f"\nNo element types registered.")
                click.echo("  Hint: Use -r to import element repository modules")
        
        await engine.dispose()
        
        click.echo("\n" + "=" * 60)
        click.secho("✓ DForm schema creation complete!", fg='green', bold=True)
        click.echo("=" * 60)
        
    except Exception as e:
        raise click.ClickException(f"Failed to create DForm schema: {e}")
