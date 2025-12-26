"""DForm management commands."""

import click

from .create_schema import create_schema
from .register import register_all


@click.group()
def df_commands():
    """DForm management commands."""
    pass


df_commands.add_command(create_schema)
df_commands.add_command(register_all)
