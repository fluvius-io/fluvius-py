import configparser
import json
import logging
import os
import re

from types import ModuleType
from typing import Any, Dict, Union, Callable
from ast import literal_eval

from . import sysdefaults


def env(name: str, defval: Any, redacted: bool = False, coercer: Callable[[Any], Any] = None):
    ''' Extract environment value to use as configuration variable
    '''
    value = os.environ.get(name, defval)
    return coercer(value) if callable(coercer) else value


FLUVIUS_SYSTEM_DEFAULTS = env("FLUVIUS_SYSTEM_DEFAULTS", "sysdefaults")
FLUVIUS_CONFIG_FILES = env("FLUVIUS_CONFIG_FILE", "base.ini|config.ini").split('|')
DEBUG_ALL_CONFIG_VALUE = "#ALL"


def __module_config__():  # noqa: C901
    RX_INVALID_OPTION = re.compile(r"[^A-Za-z\d_]+")

    __parser__ = configparser.ConfigParser()
    __parser__.optionxform = lambda s: RX_INVALID_OPTION.sub("_", s.strip()).upper()

    __config__: Dict[str, "ModuleConfig"] = {}

    def readfp(fp) -> None:
        __parser__.readfp(fp)

    class ModuleConfig(object):
        def __init__(self, module_name: str, *defaults):
            if module_name in __config__:
                raise RuntimeError(f"Module [{module_name}] already configured.")

            # Do not remove this condition,
            # the section also be created as the config file is read.
            if not __parser__.has_section(module_name):
                __parser__.add_section(module_name)

            self.__name__ = module_name
            values: Dict[str, Any] = {}
            vdebug: Dict[str, Any] = {}

            def getter(section, key, value):
                # NOTE: bool is a subclass of int,
                # therefore it must be checked before int.
                if isinstance(value, bool):
                    return __parser__.getboolean(section, key)
                if isinstance(value, int):
                    return __parser__.getint(section, key)
                if isinstance(value, float):
                    return __parser__.getfloat(section, key)
                if isinstance(value, (dict, list, tuple)):
                    return json.loads(__parser__.get(section, key))
                if isinstance(value, (str, type(None))):
                    return __parser__.get(section, key)

                raise ValueError(f"Not supported config value type [{type(value)}].")

            def load_config(conf):
                if conf is None:
                    return

                if isinstance(conf, ModuleConfig):
                    _iter = conf.items()
                    _trace = conf.__vdebug__
                else:
                    _iter = conf.__dict__.items()
                    _trace = None

                for k, v in _iter:
                    if not k.isupper() or k in values:
                        continue

                    try:
                        values[k] = getter(module_name, k, v)
                        try:
                            value_lst = literal_eval(values[k])
                            if isinstance(type(value_lst), type(list)):
                                values[k] = value_lst
                        except Exception:
                            pass
                        vdebug[k] = (values[k], type(values[k]), FLUVIUS_CONFIG_FILES)
                    except configparser.NoOptionError:
                        values[k] = v
                        vdebug[k] = _trace[k] if _trace else (v, type(v), getattr(conf, '__name__', '<unknown-name>'))

            for conf in defaults + (sysdefaults,):
                load_config(conf)

            if sysdefaults.DEBUG_MODULE_CONFIG in (
                DEBUG_ALL_CONFIG_VALUE,
                module_name,
            ):
                logging.debug("=== START MODULE CONFIG [%s] ===", module_name)
                for k, v in vdebug.items():
                    logging.debug(" - [%s] %s ::= %s", k, v[0], v[1:])
                logging.debug("=/=  END MODULE CONFIG [%s]  =/=", module_name)

            self.__values__ = values
            self.__vdebug__ = vdebug

        def __getattr__(self, name):
            return self.__values__[name]

        def __getitem__(self, name):
            return self.__values__[name]

        def __gettype__(self, name):
            return self.__types__[name]

        def get(self, name):
            return self.__values__.get(name)

        def items(self):
            ''' NOTE: This function implies that `items()` only list
                keys that is UPPERCASE that is defined in defaults.py
            '''
            yield from self.__values__.items()

        def keys(self):
            ''' NOTE: This function implies that `items()` only list
                keys that is UPPERCASE that is defined in defaults.py
            '''
            yield from self.__values__.keys()

        def values(self):
            ''' NOTE: This function implies that `items()` only list
                keys that is UPPERCASE that is defined in defaults.py
            '''
            yield from self.__values__.values()

        def as_dict(self):
            return self.__values__.copy()

    def get_config(config_key: str, *defaults: Union[ModuleType, ModuleConfig]) -> ModuleConfig:
        if config_key not in __config__:
            __config__[config_key] = ModuleConfig(config_key, *defaults)

        return __config__[config_key]

    ''' Attempt to read and parse a list of filenames,
        returning a list of filenames which were successfully parsed.
        If filenames is a string or Unicode string, it is treated as
        a single filename. If a file named in filenames cannot be
        opened, that file will be ignored. This is designed so that
        you can specify a list of potential configuration file locations
        (for example, the current directory, the user's home directory,
        and some system-wide directory), and all existing configuration
        files in the list will be read
    '''
    __parser__.read(FLUVIUS_CONFIG_FILES)
    default_config = get_config(FLUVIUS_SYSTEM_DEFAULTS, sysdefaults)
    # makes an instance of the Config helper class available to all the modules
    return ModuleConfig, get_config, default_config, __config__.items


ModuleConfig, getConfig, default_config, list_config = __module_config__()
