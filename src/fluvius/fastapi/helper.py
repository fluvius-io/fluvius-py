import os
import re

from fluvius.query.helper import SCOPING_SIGN, SCOPING_SEP, PATH_QUERY_SIGN

SCOPE_SELECTOR = f"{SCOPING_SIGN}{{scope}}"
PATH_QUERY_SELECTOR = f"{PATH_QUERY_SIGN}{{path_query}}"


def uri(*elements):
    for e in elements[1:]:
        if e.startswith('/'):
            raise ValueError('Path elements must not start with `/`')

    return os.path.join(*elements)

