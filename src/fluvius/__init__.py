import importlib
import logging

from .conf import defaults

__version__ = "0.1.3-final"
__all__ = ('config', 'logger', 'setupModule')


def setupModule(module_name, *upstreams):
    from fluvius.logs import getLogger
    from fluvius.conf import getConfig

    def _config_name(module):
        if isinstance(module, str):
            for suffix in ('._meta', '.conf', '._config', '.config', '.cfg'):
                if module.endswith(suffix):
                    return module.rstrip(suffix)

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
