import logging
import os
from types import SimpleNamespace


def setup_config():
    """Setup configuration for fluvius_ordinal package."""
    config = SimpleNamespace()
    
    # Import defaults
    from .defaults import (
        CHECK_WORKING_MEMORY_ATTRS,
        DEBUG_RULE_ENGINE,
        NARRATION_RULE_RETRACTED,
        NARRATION_RULE_FAIL_PRECOND
    )
    
    # Set configuration values
    config.CHECK_WORKING_MEMORY_ATTRS = os.getenv('FLUVIUS_ORDINAL_CHECK_WM_ATTRS', 
                                                   str(CHECK_WORKING_MEMORY_ATTRS)).lower() == 'true'
    config.DEBUG_RULE_ENGINE = os.getenv('FLUVIUS_ORDINAL_DEBUG_RULES', 
                                       str(DEBUG_RULE_ENGINE)).lower() == 'true'
    config.NARRATION_RULE_RETRACTED = int(os.getenv('FLUVIUS_ORDINAL_NARRATION_RETRACTED', 
                                                   NARRATION_RULE_RETRACTED))
    config.NARRATION_RULE_FAIL_PRECOND = int(os.getenv('FLUVIUS_ORDINAL_NARRATION_FAIL_PRECOND', 
                                                      NARRATION_RULE_FAIL_PRECOND))
    
    return config


def setup_logger():
    """Setup logger for fluvius_ordinal package."""
    logger = logging.getLogger('fluvius_ordinal')
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


# Initialize config and logger
config = setup_config()
logger = setup_logger()
