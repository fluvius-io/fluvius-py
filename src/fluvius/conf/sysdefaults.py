''' When all lookups failed. This module provides a last chance to get a config value.
    i.e. A system level default values for Config variables.

    If a variable is not defined in this file, it will throw an error if the following
    checks failed:
        - a configuration in the default configuration file (in the correct section)
        - a default value in `defaults.py`
'''

LOG_LEVEL = "info"
LOG_FORMATTER_LONG = (
    "[%(asctime)-15s] [{hostname}] "
    "%(process)3d %(levelname)-6s "
    "[%(name)16.16s - %(filename)16.16s:%(lineno)-4d] "
    "%(message)s"
)
LOG_FORMATTER_SHORT = (
    "[%(asctime)-8s] "
    "%(process)3d "
    "[%(name)16.16s - %(filename)16.16s:%(lineno)-4d]%(levelname)6s "
    "%(message)s"
)
LOG_DATEFMT = "%H:%M:%S"
LOG_FORMATTER = LOG_FORMATTER_SHORT
LOG_OUTPUT = None
LOG_OUTPUT_SECONDARY = None
LOG_COLORED = False

# Print module configuration. Accept the name of a module. E.g. "fluvius.query"
DEBUG_MODULE_CONFIG = None
