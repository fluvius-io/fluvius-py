"""Database management commands."""

import click

# Import and register commands
from .create_schema import create_schema
from .drop_schema import drop_schema
from .import_data import import_data
from .export_data import export_data


@click.group()
def commands():
    """Database management commands."""
    pass

commands.add_command(create_schema)
commands.add_command(drop_schema)
commands.add_command(import_data)
commands.add_command(export_data)