"""Workflow management commands."""

import click

# Import and register commands
from .import_definitions import import_definitions


@click.group()
def wf_commands():
    """Workflow management commands."""
    pass

wf_commands.add_command(import_definitions)

