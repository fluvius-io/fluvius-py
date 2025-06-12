import os
import signal
import sys
import threading
import traceback

from fluvius.helper import load_yaml
from fluvius.dmap.interface import DataProcessConfig

from . import logger

def read_config(parser_file):
    config = load_yaml(parser_file)
    basedir = os.path.dirname(parser_file)

    for key in ('tracker', 'reader', 'writer', 'pipelines'):
        if isinstance(config.get(key), str):
            config_file = os.path.join(basedir, config[key])
            config[key] = load_yaml(config_file)

    return DataProcessConfig(**config)


