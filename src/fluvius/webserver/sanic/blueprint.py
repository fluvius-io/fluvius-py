from datetime import datetime

from sanic import Blueprint
from sanic.request import Request
from sanic.response import HTTPResponse, json

from fluvius_oauth.blueprint import auth_required
from fluvius.exceptions import BadRequestError
from fluvius.sanic import logger, config

from .response import response_handler
from .handler import sanic_error_handler
from .pending import pending_command_ingress


RAISE_INTERNAL_ERROR = True
DEBUG_EXCEPTION = config.DEBUG_EXCEPTION
DEBUG_INGRESS = config.DEBUG_INGRESS
IDEMPOTENCY_KEY = config.IDEMPOTENCY_KEY
RE_UUID = r'[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}'


def request_payload(request):
    def _preprocess_formdata(form_data):
        # sanic use urllib.parse.parse_qs to parse form data
        # in which it **always** wraps the value inside a list
        # this process to formalize data as simple key, value
        for key, values in form_data.items():
            if len(values) > 1:
                raise BadRequestError(
                    errcode=400288,
                    message=f"Ambiguous form values (i.e. multiple value provided). Key = {key}",
                )

            if len(values) != 1:
                continue

            yield key, values[0]

    content_type = request.headers.get("content-type", "")

    if content_type.startswith("application/json"):
        return request.json

    if content_type.startswith("application/x-www-form-urlencoded"):
        return dict(_preprocess_formdata(request.form))

    if content_type.startswith("multipart/form-data"):
        form_data = dict(request.form, **request.files)
        return dict(_preprocess_formdata(form_data))

    raise BadRequestError(
        errcode=400289, message=f"Invalid request content-type: {content_type}")


def setup_domain_blueprint(domain_cls, connector, auth_decorator=auth_required):
    domain_name = domain_cls.get_name()
    domain = domain_cls(connector)
    domain_prefix = domain_cls.__namespace__
    api_revision = domain_cls.__revision__
    version = domain_cls.__version__

    @sanic_error_handler
    @auth_decorator
    async def _command_ingress(
            request: Request,
            user,
            cmd_key,
            resource,
            item_id=None,
            dataset_id=None
    ) -> HTTPResponse:
        cmd_data = request_payload(request)
        context = request.ctx.domain_context.set(_user=user, dataset_id=dataset_id, user_id=user._id)
        aggroot = domain.create_aggroot(resource, item_id)
        command = domain.create_command(aggroot, cmd_key, cmd_data)
        responses, _ = await domain.process_request(context, command)
        return response_handler(request, responses)

    async def _domain_status(request):
        return json(
            {
                "domain": domain_name,
                "namespace": domain_prefix,
                "version": version,
                "api_revision": api_revision,
                "timestamp": str(datetime.utcnow()),
                "supported_commands": sorted(
                    [cmd for cmd, _ in domain_cls.enumerate_command()]),
            }
        )

    item_id = rf"<item_id:{RE_UUID}?>"
    dataset_id = rf"<dataset_id:~({RE_UUID})>"  # noqa: W605
    batch_id = rf"<batch_id:{RE_UUID}?>"
    resource = r"<resource:[A-z0-9][A-z0-9\-_]*[A-z0-9]?>"
    command_key = r"<cmd_key:@([a-z\d\-]+)>"

    resource_path = f"/{command_key}/{resource}"
    dataset_resource_path = f"/{dataset_id}/{command_key}/{resource}"
    item_path = f"{resource_path}/{item_id}"
    dataset_item_path = rf"{dataset_resource_path}/{item_id}"

    bp = Blueprint(domain_name, url_prefix=domain_prefix)
    bp.add_route(_domain_status, r"/~status/", name=f"{domain_name}_status")
    bp.add_route(_command_ingress, resource_path, methods=["POST"], name=f"{domain_name}_resource")
    bp.add_route(_command_ingress, item_path, methods=["POST", "PATCH", "DELETE"], name=f"{domain_name}_item")
    bp.add_route(_command_ingress, dataset_resource_path, methods=["POST"], name=f"{domain_name}_dataset_resource")
    bp.add_route(
        _command_ingress, dataset_item_path,
        methods=["POST", "PATCH", "DELETE"],
        name=f"{domain_name}_dataset_item")

    # Pending command processing ...

    @sanic_error_handler
    @auth_decorator
    async def _pending_command_ingress(
            request: Request, user, batch_id) -> HTTPResponse:
        payload = request_payload(request)
        domain = bp.ctx.get_domain_instance(
            domain_name, request, domain_name, batch_id, user=user
        )
        responses = await pending_command_ingress(domain, batch_id, user, payload)
        return response_handler(request, responses)

    pending_command_path = f"/pending-command/{batch_id}"
    bp.add_route(
        _pending_command_ingress, pending_command_path,
        methods=["POST", "PATCH", "DELETE"],
        name=f"{domain_name}_pending_command"
    )

    logger.debug("Registered domain blueprint [%s] @ /%s", domain_name, domain_prefix)
    return bp
