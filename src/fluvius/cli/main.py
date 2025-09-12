#!/usr/bin/env python3
"""Fluvius command line control tool."""

import click
from flvctl import db, run


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Fluvius command line control tool."""
    pass


# Register command groups
cli.add_command(db.commands, name="db")
cli.add_command(run.commands, name="run")
