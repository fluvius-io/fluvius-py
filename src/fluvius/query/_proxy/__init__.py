import re
from functools import partial
from fluvius_query import logger, config
from . import proxy_xaccel, proxy_raw_sql


def select_request_handler(api_endpoint, query_delegate=None):

    # @TODO: find better way to select queyr sql delegate
    if query_delegate and query_delegate == "PROXY_RAW_SQL":
        return partial(proxy_raw_sql.delegate, api_endpoint)

    # Prepare delegating function
    if api_endpoint and not re.match(r"^https?://", api_endpoint):
        return partial(proxy_xaccel.delegate, api_endpoint)

    if config.QUERY_DELEGATE_METHOD == 'AIO':
        from . import proxy_asyncio
        logger.info("Using asyncio forward [%s]. Should use [x-accel] instead.", api_endpoint)
        return partial(proxy_asyncio.delegate, api_endpoint)

    if config.QUERY_DELEGATE_METHOD == 'REQ':
        from . import proxy_requests
        logger.info("Using requests forward [%s]. Should use [x-accel] instead.", api_endpoint)
        return partial(proxy_requests.delegate, api_endpoint)

    raise ValueError(f'Invalid config.QUERY_DELEGATE_METHOD = {config.QUERY_DELEGATE_METHOD}  (Allow: REQ, AIO)')
