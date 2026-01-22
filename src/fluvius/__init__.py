from ast import Module
from types import ModuleType
from typing import List, Tuple
import importlib
import logging

from .conf import defaults

__version__ = "0.2.0-rc0"
__all__ = ('config', 'logger', 'setupModule')


def setupModule(module_name: str, *upstreams: List[Module]) -> Tuple[ModuleType, logging.Logger]:
    from fluvius.logs import getLogger
    from fluvius.conf import getConfig

    def _config_name(module: str) -> str:
        for suffix in ('._meta', '.conf', '._config', '.config', '.cfg'):
            if module.endswith(suffix):
                return module.removesuffix(suffix)

        return module

    config_key = _config_name(module_name)

    if not upstreams:
        try:
            upstreams = (importlib.import_module(f"{module_name}.defaults"),)
        except ImportError as e:
            logging.warning(
                f"Unable to import configuration defaults for module [{module_name}]. {e}"
            )

    config = getConfig(config_key, *upstreams)
    logger = getLogger(config_key, config)
    return config, logger


# Setup the default config and logger
config, logger = setupModule(__name__, defaults)
