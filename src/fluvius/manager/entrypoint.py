"""Fluvius command line control tool."""

import click

from . import db, run
from .. import __version__

@click.group(invoke_without_command=True)
@click.pass_context
@click.version_option(version=__version__)
def fluvius_manager(ctx):
    """Fluvius command line control tool."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# Register command groups
fluvius_manager.add_command(db.db_commands, name="db")
fluvius_manager.add_command(run.run_commands, name="run")
