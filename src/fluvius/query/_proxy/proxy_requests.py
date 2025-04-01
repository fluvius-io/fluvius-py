import requests
from sanic.response import raw
from fluvius_query import config, logger

DEBUG_QUERY = config.DEBUG_QUERY


async def delegate(api_prefix: str, uri: str, params: dict, headers: dict = None, resp_headers: dict = None, request=None):
    if api_prefix:
        uri = f"{api_prefix}/{uri}"

    hdr = {"accept": "application/json"}
    if isinstance(headers, dict):
        hdr.update(headers)

    resp = requests.get(uri, headers=hdr, params=params)
    DEBUG_QUERY and logger.debug(
        "REQUEST [%s] => params: %s, headers %s", uri, params, hdr)

    resp_hdr = {
        "content-type": resp.headers.get("content-type"),
        "content-range": resp.headers.get("content-range"),
    }

    if resp_headers:
        resp_hdr.update(resp_headers)

    return raw(
        resp.content,
        status=resp.status_code,
        headers=resp_hdr,
    )
