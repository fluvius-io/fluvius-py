from .conf import defaults
from .base import setupModule

config, logger = setupModule(__name__, defaults)

__all__ = ('config', 'logger', 'setupModule')
