import importlib
import logging

from fluvius.conf import defaults

CONFIG_SUFFIXES = ('.cfg', '._cfg', '._config', '.config')

def _config_name(module):
    if isinstance(module, str):
        for suffix in CONFIG_SUFFIXES:
            if module.endswith(suffix):
                return module.rstrip(suffix)

    return module


def setupModule(module_name, *upstreams):
    from fluvius.logs import getLogger
    from fluvius.conf import getConfig

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

