"""Import data command."""

import click
import glob
import os
import pandas as pd
import sqlalchemy as sa

from ._common import load_connector_class, get_schema_name, convert_to_async_dsn, async_command, create_async_engine

@click.command()
@click.argument('connector_import', type=str)
@click.argument('data_folder', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--force', is_flag=True, help='Overwrite existing data in tables')
@click.option('--batch-size', default=1000, help='Number of rows to insert in each batch')
@async_command
async def import_data(connector_import: str, data_folder: str, force: bool, batch_size: int):
    """Import CSV files from a folder into database tables.
    
    CONNECTOR_IMPORT: Import string to the SqlaDriver connector class
                      (e.g., 'riparius.WorkflowConnector')
    DATA_FOLDER: Path to folder containing CSV files
    """
    try:
        # Load the connector class using shared function
        connector_class = load_connector_class(connector_import)
        schema_name = get_schema_name(connector_class)
        
        # Convert to async DSN and create engine
        async_dsn = convert_to_async_dsn(connector_class.__db_dsn__)
        engine = create_async_engine(async_dsn)
        
        # Get all CSV files in the folder
        csv_pattern = os.path.join(data_folder, "*.csv")
        csv_files = glob.glob(csv_pattern)
        
        if not csv_files:
            click.echo(f"No CSV files found in {data_folder}")
            return
        
        click.echo(f"Found {len(csv_files)} CSV files to process")
        
        async with engine.begin() as conn:
            # Get table mapping from metadata
            if hasattr(connector_class, '__data_schema_base__'):
                base_schema = connector_class.__data_schema_base__
                tables = base_schema.metadata.tables
                
                for csv_file in csv_files:
                    # Get table name from CSV filename (without extension)
                    table_name = os.path.splitext(os.path.basename(csv_file))[0]
                    full_table_name = f"{schema_name}.{table_name}"
                    
                    # Check if table exists
                    if full_table_name not in tables:
                        click.echo(f"Warning: No table found for CSV file '{csv_file}' (table: {full_table_name})")
                        continue
                    
                    table = tables[full_table_name]
                    click.echo(f"Importing data from '{csv_file}' into table '{full_table_name}'")
                    
                    try:
                        # Read CSV file
                        df = pd.read_csv(csv_file)
                        click.echo(f"  Found {len(df)} rows in CSV")
                        
                        # Check if table has data (if not forcing)
                        if not force:
                            result = await conn.execute(sa.text(f'SELECT COUNT(*) FROM {full_table_name}'))
                            count = result.scalar()
                            if count > 0:
                                click.echo(f"  Table '{full_table_name}' already has {count} rows. Use --force to overwrite.")
                                continue
                        
                        # Convert DataFrame to list of dictionaries for insertion
                        data = df.to_dict('records')
                        
                        # Insert data in batches
                        total_inserted = 0
                        for i in range(0, len(data), batch_size):
                            batch = data[i:i + batch_size]
                            
                            # Insert batch
                            await conn.execute(table.insert(), batch)
                            total_inserted += len(batch)
                            
                            click.echo(f"  Inserted batch {i//batch_size + 1}: {len(batch)} rows")
                        
                        click.echo(f"  Successfully imported {total_inserted} rows into '{full_table_name}'")
                        
                    except Exception as e:
                        click.echo(f"  Error importing '{csv_file}': {e}")
                        if not force:
                            raise
            else:
                click.echo("No base schema found in connector.")
        
        await engine.dispose()
        click.echo("Data import completed!")
            
    except Exception as e:
        raise click.ClickException(f"Failed to import data: {e}") 