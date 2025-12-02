import os
import re
import secrets

from fluvius.query.helper import SCOPING_SIGN, SCOPING_SEP, PATH_QUERY_SIGN
from fluvius.fastapi import config
from fluvius.error import BadRequestError

SCOPE_SELECTOR = "{scope}"
PATH_QUERY_SELECTOR = f"{PATH_QUERY_SIGN}{{path_query}}"


def uri(*elements):
    for e in elements[1:]:
        if e.startswith('/'):
            raise BadRequestError('S00.202', 'Path elements must not start with `/`')

    return os.path.join(*elements)


def generate_client_token(session):
    if client_token := session.get(config.SES_CLIENT_TOKEN_FIELD):
        return client_token

    client_token = secrets.token_urlsafe()
    session[config.SES_CLIENT_TOKEN_FIELD] = client_token
    return client_token

def generate_session_id(session):
    if session_id := session.get(config.SES_SESSION_ID_FIELD):
        return session_id

    session_id = secrets.token_urlsafe()
    session[config.SES_SESSION_ID_FIELD] = session_id
    return session_id