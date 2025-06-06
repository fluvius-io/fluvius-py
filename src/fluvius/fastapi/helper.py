import os
import jsonurl_py

SCOPING_SIGN = ':'
SCOPING_SEP = '='
PATH_QUERY_SIGN = "~"
SCOPES_SELECTOR = f"{SCOPING_SIGN}{{scopes}}"
PATH_QUERY_SELECTOR = f"{PATH_QUERY_SIGN}{{path_query}}"


def uri(*elements):
    for e in elements[1:]:
        if e.startswith('/'):
            raise ValueError('Path elements must not start with `/`')

    return os.path.join(*elements)


def jurl_data(data):
    '''
    Follow: https://jsonurl.org/
    ... with the start and ending brackets remove, since it needs to be alway an object.
    ... the path queries is designed to be used with query builder components (front-end) where it has
    some pre-defined query conditions.

    e.g. /~abc.eq:def,ghi.in:(1,2,3)/ -> {"abc.eq": "def", "ghi.in": [1,2,3]}
    '''

    if not data:
        return None

    return jsonurl_py.loads("(" + data + ")")


def parse_scopes(scoping_stmt, scope_schema={}):
    '''
    Scoping parameters are designed bo the used in conjunction with the
    permission system to generate a scoping query for the dataset
    and also to to check if user have access to the base resource.

    /:domain_sid_value:key=value:.../
    => {
        "domain_sid": "domain_sid_value",
        "key": "value"
    }

    /:399291-3838183-1838318-38182/dafadsf/...
    '''
    def _parse():
        if not scoping_stmt:
            return

        for part in scoping_stmt.split(SCOPING_SIGN):
            if not part:
                continue

            key, sep, value = part.partition(SCOPING_SEP)
            if sep == '' and value == '':
                value = key
                key = 'domain_sid'
            elif key == '':
                key = 'domain_sid'

            if key not in scope_schema:
                yield (key, value)
            else:
                yield (key, scope_schema[key](value))

    return dict(_parse())
