import re
import json
import jsonurl_py
from typing import Optional, List, Dict
from fluvius.error import BadRequestError

SCOPING_SIGN = ':'
SCOPING_SEP = '='
PATH_QUERY_SIGN = "~"
RX_SCOPE_VALUE = re.compile(r'^[\w\d\_\-\.]*$')


def scope_decoder(scoping_stmt, scope_schema=None):
    '''
    Scoping parameters are designed bo the used in conjunction with the
    permission system to generate a scoping query for the dataset
    and also to to check if user have access to the base resource.

    /domain_sid_value:key=value:.../
    => {
        "domain_sid": "domain_sid_value",
        "key": "value"
    }

    /399291-3838183-1838318-38182/dafadsf/...
    '''

    if not scoping_stmt:
        return None
    
    default_key = getattr(scope_schema, '__default_key__', 'domain_sid') if scope_schema else 'domain_sid'

    def _parse(stmt):
        for part in stmt.split(SCOPING_SIGN):
            part = part.strip()

            if not part:
                continue

            key, sep, value = part.partition(SCOPING_SEP)
            if not (RX_SCOPE_VALUE.match(value) and RX_SCOPE_VALUE.match(key)):
                raise ValueError(f'Invalid scoping value: {part}')

            if sep == '' and value == '':
                value = key
                key = default_key
            elif key == '':
                key = default_key

            yield (key, value)

    scope_value = dict(_parse(scoping_stmt))
    if not scope_value:
        return None

    if scope_schema:
        return scope_schema(**scope_value).model_dump()

    return scope_value


def list_decoder(data: Optional[str]) -> Optional[List[str]]:
    if not data:
        return None

    try:
        return [v.strip() for v in data.split(',') if v.strip()]
    except Exception as e:
        raise BadRequestError("Q101-503", f"Invalid list value: {data}", str(e))


def json_decoder(data: Optional[str]) -> Optional[Dict]:
    if not data:
        return None

    try:
        result = json.loads(data)

        if not isinstance(result, dict):
            raise ValueError(f"Invalid query statement: {data}")

        return result
    except json.JSONDecodeError as e:
        raise BadRequestError("Q101-503", "Invalid query value.", str(e))


def jurl_decoder(data):
    '''
    Follow: https://jsonurl.org/
    ... with the start and ending brackets remove, since it needs to be alway an object.
    ... the path queries is designed to be used with query builder components (front-end) where it has
    some pre-defined query conditions.

    e.g. /~abc.eq:def,ghi.in:(1,2,3)/ -> {"abc.eq": "def", "ghi.in": [1,2,3]}
    '''

    if not data:
        return None

    result = jsonurl_py.loads("(" + data + ")")

    if not isinstance(result, dict):
        raise ValueError(f"Invalid path query: {data}")

    return result
