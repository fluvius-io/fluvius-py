"""Workflow management commands."""

import click

# Import and register commands
from .register import register


@click.group()
def wf_commands():
    """Workflow management commands."""
    pass

wf_commands.add_command(register)

