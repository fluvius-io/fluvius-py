"""Import workflow definitions command."""

import click
from ..helper import async_command


@click.command()
@click.option('--force', is_flag=True, help='Update existing workflow definitions')
@click.option('--repository', '-r', type=str, multiple=True,
              help='Workflow repository to import definitions from')
@async_command
async def import_definitions(force: bool, repository: list[str]):
    """Import workflow definitions from registered workflows into the database.
    
    This command extracts metadata from all registered workflows and stores
    them in the workflow_definition table. By default, it only inserts new
    definitions. Use --force to update existing ones.
    
    Example:
        fluvius wf import-definitions
        fluvius wf import-definitions --force
        fluvius wf import-definitions --repository my_app.workflow_a --repository my_app.workflow_b
    """
    from fluvius.navis.engine.manager import WorkflowManager
    from fluvius.navis.model import WorkflowDataManager
    
    click.echo("=" * 80)
    click.echo("Workflow Definition Import")
    click.echo("=" * 80)
    
    
    click.echo("\nGenerating workflow definitions...")
    
    # Generate workflow definitions from registered workflows
    wfdefs = WorkflowManager.gen_wfdefs(*repository)
    
    if not wfdefs:
        click.echo("No workflow definitions generated.")
        return
    
    click.echo(f"Generated {len(wfdefs)} workflow definition(s)")
    click.echo("\nImporting into database...")
    
    # Create data manager
    data_manager = WorkflowDataManager()
    
    # Import each workflow definition
    inserted = 0
    updated = 0
    skipped = 0
    errors = []
    async with data_manager.transaction() as tx:
        for wfdef in wfdefs:
            try:
                # Check if definition already exists
                existing = None
                try:
                    existing = await data_manager.find_one(
                        'workflow_definition',
                        where={
                            'wfdef_key': wfdef['wfdef_key'],
                            'wfdef_rev': wfdef['wfdef_rev']
                        }
                    )
                except Exception:
                    # No existing definition found
                    pass
                
                if not existing:
                    # Insert new definition
                    await data_manager.insert_data('workflow_definition', wfdef)
                    inserted += 1
                    click.echo(f"  ✓ Inserted: {wfdef['wfdef_key']} (rev {wfdef['wfdef_rev']})")
                    continue

                if not force:
                    skipped += 1
                    click.echo(f"  − Skipped: {wfdef['wfdef_key']} (rev {wfdef['wfdef_rev']}) - already exists")
                    continue

                # Update existing definition
                await data_manager.update_data(
                    'workflow_definition',
                    existing['_id'],
                    **wfdef
                )
                updated += 1
                click.echo(f"  ↻ Updated: {wfdef['wfdef_key']} (rev {wfdef['wfdef_rev']})")
            except Exception as e:
                error_msg = f"Error importing {wfdef['wfdef_key']}: {str(e)}"
                errors.append(error_msg)
                click.echo(f"  ✗ Error: {wfdef['wfdef_key']} - {str(e)}", err=True)
        
    # Display summary
    click.echo("\n" + "=" * 80)
    click.echo("Import Results")
    click.echo("=" * 80)
    click.echo(f"\nTotal workflows processed: {len(wfdefs)}")
    click.echo(f"  ✓ Inserted: {inserted}")
    click.echo(f"  ↻ Updated:  {updated}")
    click.echo(f"  − Skipped:  {skipped}")
    click.echo(f"  ✗ Errors:   {len(errors)}")
    
    if errors:
        click.echo("\nError Details:")
        for error in errors:
            click.echo(f"  ! {error}")
    
    click.echo("\n" + "=" * 80)
    
    if inserted > 0 or updated > 0:
        click.secho("✓ Workflow definitions successfully imported!", fg='green', bold=True)
    elif skipped > 0:
        click.secho("→ All workflow definitions already exist. Use --force to update.", fg='yellow')
    else:
        click.echo("→ No workflow definitions imported.")
        
    click.echo("=" * 80)
    
    # Exit with error code if there were errors
    if len(errors) > 0:
        raise click.ClickException(f"{len(errors)} error(s) occurred during import")
        
