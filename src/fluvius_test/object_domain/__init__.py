from .cfg import config, logger

from . import aggregate, domain, command, event
from .domain import ObjectDomain


__version__ = '1.0.0'
__all__ = ("ObjectDomain", "command", "event", "ObjectDAL", "aggregate", "domain", "config", "logger")
