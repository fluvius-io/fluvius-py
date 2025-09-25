#!/usr/bin/env python3
"""Fluvius command line control tool."""

import click
from . import db, run

@click.group()
@click.version_option(version="1.0.0")
def fluvius_manager():
    """Fluvius command line control tool."""
    pass


# Register command groups
fluvius_manager.add_command(db.db_commands, name="db")
fluvius_manager.add_command(run.run_commands, name="run")
