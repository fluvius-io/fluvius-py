import aiohttp
from sanic.response import raw
from fluvius_query import config, logger

DEBUG_QUERY = config.DEBUG_QUERY


async def delegate(
    api_prefix: str,
    uri: str,
    params: dict,
    headers: dict = None,
    resp_headers: dict = None,
    request=None
):
    if api_prefix:
        uri = f"{api_prefix}/{uri}"

    hdr = {"accept": "application/json"}
    if isinstance(headers, dict):
        hdr.update(headers)

    session = aiohttp.ClientSession()
    resp = await session.get(uri, params=params, headers=hdr)
    content = await resp.read()
    await session.close()

    resp_hdr = {
        "content-type": resp.headers.get("content-type"),
        "content-range": resp.headers.get("content-range"),
    }

    if resp_headers:
        resp_hdr.update(resp_headers)

    DEBUG_QUERY and logger.debug(
        "REQUEST [%s] => params: %s headers %s", uri, params, hdr)
    return raw(
        content,
        status=resp.status,
        headers=resp_hdr,
    )
