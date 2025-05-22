import functools
import inspect
import os
import re
import shutil
import tempfile
import importlib

from contextlib import contextmanager
from itertools import chain
from operator import itemgetter
from typing import Dict, List, Optional, Pattern, Tuple, Union

from fluvius.error import AssertionFailed
from fluvius import logger


RX_DELIMITER_SPLITTER = re.compile(r"[\.#]")
RX_LOWERCASE_DASH = re.compile(r'^[a-z][a-z_\-\d]*[a-z\d]$')


def validate_lower_dash(value):
    if RX_LOWERCASE_DASH.match(value):
        return value

    raise ValueError(f'Invalid lower-dash identifier: {value}')


def load_string(module_path):
    """
    Import a dotted module path and return the attribute/class designated by the
    last name in the path. Raise ImportError if the import failed.
    """
    try:
        module_path, class_name = module_path.rsplit('.', 1)
        module = importlib.import_module(module_path)
    except ValueError:
        raise ImportError("%s doesn't look like a module path" % module_path)

    try:
        return getattr(module, class_name)
    except AttributeError:
        raise ImportError('Module "%s" does not define a "%s" attribute/class' % (
            module_path, class_name))


def load_class(class_or_path, /, base_class=None):
    if isinstance(class_or_path, str):
        cls = load_string(class_or_path)
    else:
        cls = class_or_path

    if base_class and not issubclass(cls, base_class):
        raise ImportError(f'Class [{cls}] is not a subclass of [{base_class}]')

    return cls


async def when(val):
    return await val if inspect.isawaitable(val) else val


def load_yaml(filepath):
    import yaml
    with open(filepath, "r") as stream:
        data = yaml.safe_load(stream)
        return data


def listify(lst, obj=None, prefix=None):
    ''' Make sure we have a list with optional object attributes lookup
    '''
    if lst is None:
        return []

    if not isinstance(lst, (list, tuple)):
        lst = [lst]

    if obj is None:
        return lst

    if prefix and isinstance(prefix, str):
        return [getattr(obj, "{}__{}".format(prefix, item)) for item in lst]

    return [getattr(obj, item) for item in lst]


def relpath(base, path):
    ''' Relative path constructor
    '''
    basedir = os.path.dirname(os.path.realpath(base))
    return os.path.join(basedir, path)


def dcopy(*args):
    ''' Copy and merge multiple dictionaries and return the combined one.
    '''
    dr = {}
    for dx in args:
        if dx:
            dr.update(dx)
    return dr


def dget(
    dx: Optional[Union[Dict, List, Tuple]],
    key: str,
    defval=None,
    splitter: Pattern[str] = RX_DELIMITER_SPLITTER,
):
    ''' A robust way to extract values from a (presumably) dictionary or list
        This method can be proceed without error (and return default value in such cases)
        with what ever threw at it. Expected parameters are:
            - dx: a dictionary/list/tuple
            - key: a delimiter (':') separated list of keys to descend
            - defval: default value to return. Default to: None
            - delimiter: key delimiter. Default to: ':'
    '''
    try:
        for k in splitter.split(key):
            if isinstance(dx, dict):
                dv = dx[k]
            elif isinstance(dx, (list, tuple)):
                dv = dx[int(k)]
            else:
                return defval
            # Prevent advancing. This should be the last key already.
            # Next step will trigger an error
            dx = dv
    except (KeyError, IndexError, TypeError, ValueError, AttributeError):
        return defval
    # Successful lookup!
    return dv


def index_of(item, array: list) -> int:
    ''' Get the index of item in the array.
        .. returns:
            index of item if found
            -1 if not found
    '''
    try:
        return array.index(item)
    except ValueError:
        return -1


def unique(seq):
    ''' Return a list from the input sequence with only unique items. Keeping the initial order.
        .. returns:
            a list of unique item in the sequence with ordering intact (first appearance.)
    '''
    seen = set()
    seen_add = seen.add
    return [x for x in seq if not (x in seen or seen_add(x))]


def merge_order(original, update, prepend=False):
    ''' Merge orders. A quite robust solution for keeping order.
        E.g.
        >>> arrangement = ['a', 'b', 'c', 'd', 'e', 'e']
        >>> update = ['t', 'y', 'c', 'b', 'x', 'y', 'e', 'z']
        >>> merge_order(arrangement, update)
        ['t', 'y', 'a', 'c', 'b', 'x', 'd', 'e', 'z']
    '''
    try:
        if not update:
            return unique(original)

        if not original:
            return unique(update)

        original = list(original)
    except ValueError:
        return []

    # Single update and not already existed
    if len(update) == 1:
        if prepend:
            original.insert(0, update[0])
        else:
            original.append(update[0])
        return unique(original)

    old_idx = [index_of(i, original) for i in update]
    new_idx = sorted(x for x in old_idx if x >= 0)

    cursor = -1
    added = 0
    counter = 0
    for idx, item in enumerate(update):
        if old_idx[idx] != -1:
            cursor = new_idx[counter] + added
            original[cursor] = item
            counter += 1
        else:
            added += 1
            cursor += 1
            original.insert(cursor, item)

    return unique(original)


RX_CAMEL_1 = re.compile(r"(.)([A-Z][a-z]+)")
RX_CAMEL_2 = re.compile(r"([a-z0-9])([A-Z])")


def camel_to_lower(name: str):
    s1 = RX_CAMEL_1.sub(r"\1-\2", name)
    return RX_CAMEL_2.sub(r"\1-\2", s1).lower().replace("_", "-")


def camel_to_lower_underscore(name: str):
    s1 = RX_CAMEL_1.sub(r"\1_\2", name)
    return RX_CAMEL_2.sub(r"\1_\2", s1).lower().replace("-", "_").replace(".", "__")


def safe_filename(filename: str, extension: Optional[str] = None):
    if extension:
        parts = filename.split(".")
        if len(parts) > 1:
            parts = parts[:-1]
        ext = extension.split(".")
        ''' Filter for empty strings. I.e. double dots [..] '''
        filename = ".".join(filter(lambda x: x, chain(parts, ext)))
    ''' Filename sanitization. Otherwise some files won't be extractable on Windows'''
    return "".join(e for e in filename if e not in "@/\\;,><&*:%=+!#^|?")


def ensure_path(*args):
    path = os.path.join(*args)
    if not os.path.exists(path):
        os.makedirs(path)

    return path


def consume_queue(q):
    while not q.empty():
        yield q.get()
        q.task_done()


def assert_(stmt: bool, message: str, *params, code = 400001):
    if stmt:
        return

    raise AssertionFailed(code, message.format(*params))


VALUE_REQUIRED = object()
def select_value(usr_value, cls_value=None, default=VALUE_REQUIRED):
    """
        Select a proper value from mutual exclusive values provided.
        I.e. either usr_value or cls_value should be provided (is not None), not both
    """

    if usr_value is not None:
        if cls_value is not None:
            raise ValueError('Both user value and class value provided.')

        return usr_value

    if cls_value is not None:
        return cls_value

    if default is VALUE_REQUIRED:
        raise ValueError('Value is required')

    return default
