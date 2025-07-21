"""Export data command."""

import click
import sqlalchemy as sa
import pandas as pd
import os
from ._common import load_connector_class, get_schema_name, convert_to_async_dsn, async_command, create_async_engine


@click.command()
@click.argument('connector_import', type=str)
@click.argument('data_folder', type=click.Path(file_okay=False, dir_okay=True))
@click.option('--force', is_flag=True, help='Overwrite existing CSV files')
@click.option('--tables', default=None, help='Comma-separated list of tables to export')
@async_command
async def export_data(connector_import: str, data_folder: str, force: bool, tables: str = None):
    """Export data from database tables to CSV files.
    
    CONNECTOR_IMPORT: Import string to the SqlaDriver connector class
                      (e.g., 'riparius.WorkflowConnector')
    DATA_FOLDER: Path to folder where CSV files will be saved
    """
    try:
        # Load the connector class using shared function
        connector_class = load_connector_class(connector_import)
        schema_name = get_schema_name(connector_class)
        
        # Convert to async DSN and create engine
        async_dsn = convert_to_async_dsn(connector_class.__db_dsn__)
        engine = create_async_engine(async_dsn)
        
        # Create output folder if it doesn't exist
        os.makedirs(data_folder, exist_ok=True)
        
        # Parse table filter
        table_filter = None
        if tables:
            table_filter = [t.strip() for t in tables.split(',')]
        
        async with engine.begin() as conn:
            # Get table mapping from metadata
            if hasattr(connector_class, '__data_schema_base__'):
                base_schema = connector_class.__data_schema_base__
                tables_metadata = base_schema.metadata.tables
                
                exported_tables = []
                
                for table_name, table in tables_metadata.items():
                    # Skip tables not in our schema
                    if not table_name.startswith(f"{schema_name}."):
                        continue
                    
                    # Extract just the table name without schema
                    short_table_name = table_name.split('.', 1)[1]
                    
                    # Apply table filter if specified
                    if table_filter and short_table_name not in table_filter:
                        continue
                    
                    csv_file = os.path.join(data_folder, f"{short_table_name}.csv")
                    
                    # Check if CSV file exists (if not forcing)
                    if not force and os.path.exists(csv_file):
                        click.echo(f"CSV file '{csv_file}' already exists. Use --force to overwrite.")
                        continue
                    
                    click.echo(f"Exporting data from table '{table_name}' to '{csv_file}'")
                    
                    try:
                        # Query all data from the table
                        # Split schema and table name for proper quoting
                        schema_name, table_name_only = table_name.split('.', 1)
                        result = await conn.execute(sa.text(f'SELECT * FROM "{schema_name}"."{table_name_only}"'))
                        rows = result.fetchall()
                        
                        if not rows:
                            click.echo(f"  Table '{table_name}' is empty")
                            # Create empty CSV file with column headers
                            column_names = [col.name for col in table.columns]
                            empty_df = pd.DataFrame(columns=column_names)
                            empty_df.to_csv(csv_file, index=False)
                            click.echo(f"  Created empty CSV file with headers '{csv_file}'")
                        else:
                            # Convert to DataFrame
                            df = pd.DataFrame(rows)
                            df.columns = result.keys()
                            
                            # Export to CSV
                            df.to_csv(csv_file, index=False)
                            click.echo(f"  Exported {len(df)} rows to '{csv_file}'")
                        
                        exported_tables.append(short_table_name)
                        
                    except Exception as e:
                        click.echo(f"  Error exporting table '{table_name}': {e}")
                        if not force:
                            raise
                
                if exported_tables:
                    click.echo(f"Successfully exported {len(exported_tables)} tables: {', '.join(exported_tables)}")
                else:
                    click.echo("No tables were exported.")
            else:
                click.echo("No base schema found in connector.")
        
        await engine.dispose()
        click.echo("Data export completed!")
            
    except Exception as e:
        raise click.ClickException(f"Failed to export data: {e}") 