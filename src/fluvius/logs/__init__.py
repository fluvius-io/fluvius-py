''' Setup a nice formatter, configurable level, and syslog handler for logging.
    https://github.com/mitodl/flask-log/blob/master/flask_log.py
'''
import logging
import platform
import sys
from logging import handlers
from typing import Any, List, Optional

from fluvius.conf import ModuleConfig, default_config, getConfig


class NoConfigValue(Exception):
    pass


def getLoggerHandler(logspec: Optional[str] = None):
    if logspec is None or logspec == "stderr":
        return logging.StreamHandler(sys.stderr)

    if logspec == "stdout":
        return logging.StreamHandler(sys.stdout)

    if logspec.startswith("file://"):
        return logging.FileHandler(logspec[7:])

    def parse_spec(prefix, cls, defport=None):
        if logspec is None or not logspec.startswith(prefix):
            return None

        hostname, _, port = logspec[len(prefix):].partition(":")
        hostname = hostname or "localhost"
        port = int(port) if port else defport
        return cls(hostname, port)

    def wrap_syslog(host: str, port: int):
        return handlers.SysLogHandler(
            address=(host, port), facility=handlers.SysLogHandler.LOG_LOCAL0
        )

    for prefix, wrapper, defport in (
        ("syslog://", wrap_syslog, 514),
        ("udp://", handlers.DatagramHandler, None),
        ("tcp://", handlers.SocketHandler, None),
        ("unix://", handlers.SocketHandler, None),
    ):
        handler = parse_spec(prefix, wrapper, defport)
        if handler is not None:
            return handler

    raise ValueError("Cannot parse logging spec: %s" % logspec)


def __closure__():  # noqa: C901
    FLUVIUS_LOGGERS = dict()

    def setupLogger(module_name: Optional[str], log_config: ModuleConfig):
        ''' Setup the logging handlers, level and formatters.
        '''

        logger_name = (
            module_name[:-4] if module_name and module_name.endswith(".cfg") else module_name
        )
        module_logger = logging.getLogger(logger_name)

        if log_config is None:
            return module_logger

        def get_config_value(name):
            value = getattr(log_config, name, None)
            if isinstance(value, str):
                return value

            raise NoConfigValue("Invalid log config value: {} = {}".format(name, value))

        log_level = logging.NOTSET
        try:
            level_str = get_config_value("LOG_LEVEL")
            log_level = getattr(logging, level_str.upper())
        except (ValueError, NoConfigValue, AttributeError):
            pass

        module_logger.setLevel(log_level)

        log_handlers: List[Any] = []
        try:
            log_output = get_config_value("LOG_OUTPUT")
        except NoConfigValue:
            log_output = None

        if not isinstance(log_output, (list, tuple)):
            log_output = (log_output, )

        for output in log_output:
            if output:
                handler = getLoggerHandler(output)
                log_handlers.append(handler)
                # logging.info('LOGGING SPEC 2: %s => %s => %s', output, module_name, handler)
        # elif module_name is None:
        #     # Setup root logger if no output specified.
        #     log_handlers.append(getLoggerHandler())
        #     logging.info('LOGGING SPEC 1: %s', None)


        try:
            log_formatter = get_config_value("LOG_FORMATTER")
            log_datefmt = get_config_value("LOG_DATEFMT")
        except NoConfigValue:
            pass
        else:
            # Set up format for default logging
            hostname = platform.node().split(".")[0]
            formatter = log_formatter.format(hostname=hostname)

            ''' Override the default log formatter with your own.
            '''
            # Add our formatter to all the handlers
            for handler in log_handlers:
                handler.setFormatter(logging.Formatter(formatter, log_datefmt))

            if default_config.LOG_COLORED:
                import coloredlogs
                coloredlogs.install(
                    fmt=formatter,
                    level=log_level,
                    logger=module_logger
                )

        # Special case for the root logger
        if module_name is None:
            # Setup basic StreamHandler logging with format and level (do
            # setup in case we are main, or change root logger if we aren't.
            logging.basicConfig(handlers=log_handlers)
        else:
            for handler in log_handlers:
                module_logger.addHandler(handler)

        FLUVIUS_LOGGERS[module_name] = module_logger
        return module_logger

    def getLogger(module_name, log_config=None):
        if module_name in FLUVIUS_LOGGERS:
            return FLUVIUS_LOGGERS[module_name]

        log_config = log_config or getConfig(module_name)
        return setupLogger(module_name, log_config)

    return getLogger, setupLogger(None, default_config)


getLogger, default_logger = __closure__()
