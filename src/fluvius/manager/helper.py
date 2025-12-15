"""Fluvius command line control tool.""" 
import asyncio
import functools
import click
import importlib

def async_command(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))
    return wrapper

def import_modules(repositories: list[str]) -> int:
    """Import repositories to register classes."""
    imported = 0
    for repo in repositories:
        importlib.import_module(repo)
        click.echo(f"  ✓ Imported: {repo}")
        imported += 1
    return imported