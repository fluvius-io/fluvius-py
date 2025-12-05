import os
import re
import secrets

from fluvius.query.helper import SCOPING_SIGN, SCOPING_SEP, PATH_QUERY_SIGN
from fluvius.fastapi import config
from fluvius.error import BadRequestError

SCOPE_SELECTOR = "{scope}"
PATH_QUERY_SELECTOR = f"{PATH_QUERY_SIGN}{{path_query}}"
SAFE_REDIRECT_DOMAINS = config.SAFE_REDIRECT_DOMAINS


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


def is_safe_redirect_url(url: str) -> bool:
    """
    Validates if a given URL is a safe redirect:
    - It's either relative (no scheme or netloc),
    - Or it's an absolute URL pointing to a whitelisted domain.

    Args:
        url (str): The URL to validate.
        whitelist_domains (list[str]): List of allowed domains (e.g. ["example.com"]).

    Returns:
        bool: True if safe, False otherwise.
    """
    try:
        if not url:
            return False

        parsed = urlparse(url)

        # Case 1: Relative URL (e.g., "/login")
        if not parsed.netloc and not parsed.scheme:
            return True

        # Case 2: Absolute URL with whitelisted domain
        domain = parsed.hostname

        if '*' in SAFE_REDIRECT_DOMAINS:
            return True

        if domain and domain.lower() in SAFE_REDIRECT_DOMAINS:
            return True

        return False

    except Exception:
        return False


def validate_direct_url(url: str, default: str) -> str:
    if is_safe_redirect_url(url):
        return url

    return default
