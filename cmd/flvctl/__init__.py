"""Fluvius command line control tool.""" 
import asyncio
import functools


def async_command(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))
    return wrapper
