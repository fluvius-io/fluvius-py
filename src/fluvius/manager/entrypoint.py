"""Fluvius command line control tool."""

import click

from fluvius import logger, config

from . import db, run, wf
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
fluvius_manager.add_command(wf.wf_commands, name="wf")


try:
    from trogon import tui
    fluvius_manager = tui(command="ui", help="Open terminal UI")(fluvius_manager)
except ImportError:
    logger.info('Troggon is not available')
