from urllib.parse import quote_plus
from sanic.response import redirect
from fluvius_query import config, logger


async def delegate(
    api_endpoint: str,
    uri: str,
    params: dict,
    headers: dict = None,
    resp_headers: dict = None,
    request=None
):
    ''' Query handler '''

    if params:
        param_str = "&".join(f"{k}={quote_plus(v)}" for k, v in params.items())
        uri = f"{uri}?{param_str}"

    resp = redirect(api_endpoint)
    resp.headers["X-Accel-Redirect"] = api_endpoint
    resp.headers["X-Accel-Redirect-Uri"] = uri

    if isinstance(headers, dict):
        resp.headers.update(headers)

    if isinstance(resp_headers, dict):
        resp.headers.update(resp_headers)

    logger.info("REDIRECT %s [%s] => %s", api_endpoint, uri, resp_headers)
    return resp
