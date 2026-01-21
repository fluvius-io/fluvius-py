import click
import json
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import create_async_engine

from fluvius.manager import config
from fluvius.dform import config as dform_config    
from fluvius.dform.element import ElementModelRegistry
from fluvius.dform.form import FormModelRegistry
from fluvius.dform.schema import ElementRegistry, FormRegistry
from fluvius.manager.db.base import convert_to_async_dsn, async_command
from fluvius.manager.helper import import_modules

@click.command("register")
@click.option('--repositories', '-r', type=str, multiple=True,
              help='Repository modules to import (e.g. myapp.forms)')
@click.option('--update', is_flag=True, help='Update existing entries')
@async_command
async def register(repositories, update):
    """Register all defined elements and forms in the database."""
    
    # Import repositories
    import_modules(repositories or config.DFORM_REPOSITORIES)
    
    dsn = dform_config.DB_DSN
    async_dsn = convert_to_async_dsn(dsn)
    engine = create_async_engine(async_dsn)
    
    click.echo(f"Registering dform components...")
    
    async with engine.begin() as conn:
        # 1. Register Elements
        elements = ElementModelRegistry.values()
        if elements:
            click.echo(f"Processing {len(elements)} elements...")
            for model in elements:
                key = model.Meta.key
                schema = model.model_json_schema()
                title = model.Meta.title
                
                # Upsert
                stmt = insert(ElementRegistry).values(
                    element_key=key,
                    element_label=title,
                    element_schema=schema,
                    # defaults
                    serial_no=1 # Sequence usually handles this, might need to exclude
                )
                # handle serial_no: usually DB handles it. But insert().values() might need explicit exclusion if not passed?
                # Actually, better to simply let DB handle defaults if we don't pass them.
                
                values = {
                    'element_key': key,
                    'element_label': title,
                    'element_schema': schema
                }
                
                stmt = insert(ElementRegistry).values(**values)
                
                if update:
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['element_key'],
                        set_={
                            'element_label': title,
                            'element_schema': schema
                        }
                    )
                else:
                    stmt = stmt.on_conflict_do_nothing(index_elements=['element_key'])
                
                await conn.execute(stmt)
                click.echo(f"  ✓ Element: {key}")
        
        # 2. Register Forms
        forms = FormModelRegistry.values()
        if forms:
            click.echo(f"\nProcessing {len(forms)} forms...")
            for model in forms:
                key = model.Meta.key
                title = model.Meta.name
                desc = model.Meta.desc
                
                values = {
                    'form_key': key,
                    'title': title,
                    'desc': desc
                }
                
                stmt = insert(FormRegistry).values(**values)
                
                if update:
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['form_key'],
                        set_={
                            'title': title,
                            'desc': desc
                        }
                    )
                else:
                    stmt = stmt.on_conflict_do_nothing(index_elements=['form_key'])
                
                await conn.execute(stmt)
                click.echo(f"  ✓ Form: {key}")
                
    await engine.dispose()
    click.echo("\nRegistration complete.")
