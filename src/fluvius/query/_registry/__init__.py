def __sif__():
    RESOURCE_DOMAIN = dict()
    from .resource import model

    def _register(resource, url_prefix, default_schema):
        if not issubclass(resource, model.QueryModel):
            raise ValueError(f'Invalid query resource: {resource}')

        endpoint = resource._init_resource(url_prefix, default_schema)
        if (url_prefix, endpoint) in RESOURCE_DOMAIN:
            raise ValueError(
                "Resource already initialized / registered [%s]" % endpoint
            )

        RESOURCE_DOMAIN[url_prefix, endpoint] = resource
        return resource

    def _get_resource(*args):
        return RESOURCE_DOMAIN[args]

    return _register, _get_resource, RESOURCE_DOMAIN.items


register, get_resource, resource_items = __sif__()


from functools import wraps
from sanic.request import Request
from sanic.response import HTTPResponse, json
from fluvius_oauth import auth_required
from fluvius.sanic import sanic_error_handler

from fluvius_query import config, logger, parser, registry
from fluvius_query.builder import PostgRESTBuilder
from fluvius_query.proxy import select_request_handler
from fluvius_policy import check_query

from .model import QueryModel

DEBUG_QUERY = config.DEBUG_QUERY
QUERY_PERMISSION = config.QUERY_PERMISSION
DEFAULT_PERMISSION_RESOURCE = config.DEFAULT_PERMISSION_RESOURCE
ARG_DATASET = rf"<dataset_id:~([a-f0-9][a-f0-9\-_]*[a-f0-9])>"


def no_auth(func):
    @wraps(func)
    def _decorated(request: Request, *args, **kwargs):
        return func(request, None, *args, **kwargs)

    return _decorated


def select_auth_decorator(_auth_decorator):
    # Prepare auth_decorator
    if _auth_decorator is True:
        return auth_required

    if _auth_decorator in (None, False):
        return no_auth

    if callable(_auth_decorator):
        return _auth_decorator

    raise ValueError(
        "[auth_decorator] must be either "
        "True (auth_required), None (no_auth) or a custom decorator."
    )


def register_resource(
    app,
    api_endpoint,
    default_schema=None,
    url_prefix="",
    query_builder=PostgRESTBuilder,
    auth_decorator=True,
    query_delegate=None,
    permission=DEFAULT_PERMISSION_RESOURCE,
):
    DEBUG_QUERY and logger.info(
        "QUERY FWD [%s] (auth = %s) => %s ", url_prefix, auth_decorator, api_endpoint
    )

    auth_decorator = select_auth_decorator(auth_decorator)
    # Prepare delegating function
    delegate = select_request_handler(api_endpoint, query_delegate=query_delegate)

    def _decorator(resource: QueryModel):
        registry.register(resource, url_prefix, default_schema)

        if getattr(resource, "__internal__", None):
            return logger.info("Internal resource: %s", resource)

        builder = query_builder(resource)

        if not resource.__disable_resource_view__:

            @sanic_error_handler
            @auth_decorator
            async def query_resource_view(
                request: Request, user, dataset_id=None, **url_params
            ) -> HTTPResponse:
                parsed_query = parser.parse_query(
                    resource, request.args, request.headers, url_prefix, url_params, dataset_id
                )
                permission_query = (
                    await check_query(request.app.ctx, user, resource, parsed_query, ** request.args)
                    if (QUERY_PERMISSION and permission)
                    else {}
                )
                params, headers = builder.build_resource_query(
                    parsed_query, user, permission_query)

                return await delegate(resource.__table__, params, headers, request=request)

            if resource.__dataset_support__ is not None:
                resource_url = rf"{url_prefix}/{ARG_DATASET}/{resource.__endpoint__}"
            else:
                resource_url = f"{url_prefix}/{resource.__endpoint__}"

            app.route(resource_url)(query_resource_view)

        if not resource.__disable_item_view__:

            @sanic_error_handler
            @auth_decorator
            async def query_item_view(
                request: Request, user, identifier, dataset_id=None, **url_params
            ) -> HTTPResponse:
                parsed_query = parser.parse_query(
                    resource, request.args, request.headers, url_prefix, url_params, dataset_id
                )
                permission_query = (
                    await check_query(request.app.ctx, user, resource, parsed_query, ** request.args)
                    if (
                        QUERY_PERMISSION
                        and permission
                    )
                    else {}
                )
                params, headers = builder.build_item_query(
                    parsed_query, user, identifier, permission_query
                )

                return await delegate(resource.__table__, params, headers)

            if resource.__dataset_support__ is not None:
                item_url = rf"{url_prefix}/{ARG_DATASET}/{resource.__endpoint__}/<identifier>"
            else:
                item_url = f"{url_prefix}/{resource.__endpoint__}/<identifier>"
            app.route(item_url)(query_item_view)

        if not resource.__disable_meta_view__:

            @app.route(f"{url_prefix}/{resource.__endpoint__}/~meta")
            @sanic_error_handler
            @auth_decorator
            async def query_meta(request: Request, user, **url_params):
                return json(resource.meta())

        DEBUG_QUERY and logger.info(
            "Registered QUERY [%s] : %s", resource.__endpoint__, resource.__resource_identifier__
        )
        return resource

    return _decorator


def register_resource_meta(app, url_prefix):
    @app.route(f"{url_prefix}/~meta")
    @sanic_error_handler
    @auth_required
    def resource_meta(request: Request, user):
        return json(
            {f"{p}/{e}": r.meta()
             for (p, e), r in registry.resource_items() if p == url_prefix}
        )
