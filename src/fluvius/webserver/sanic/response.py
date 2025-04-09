from fluvius.sanic import logger, config  # noqa
from sanic import response
from fluvius.data.serializer import serialize_json
from fluvius.domain.entity import CQRS_ENTITY_KEY
from fluvius.error import BadRequestError


RAISE_INTERNAL_ERROR = True
RESPONSE_STATUS = config.RESPONSE_STATUS_KEY
DEFAULT_ACCEPT_HEADER = config.DEFAULT_ACCEPT_HEADER


def json_response(data, *args, **kwargs) -> response.HTTPResponse:
    return response.json(data, dumps=serialize_json, *args, **kwargs)


def check_data_response(responses) -> dict:
    if len(responses) != 1:
        raise BadRequestError("L9011", "Multiple/no [%s] responses received." % len(responses))

    return responses[0].data if responses[0].data else dict()


def check_text_response(responses) -> str:
    if len(responses) != 1:
        raise BadRequestError("L9011", "Multiple/no [%s] responses received." % len(responses))

    return responses[0].data if responses[0].data else ""


def response_handler(request, responses) -> response.HTTPResponse:
    accept_hdr = request.args.get("_accept") or request.headers.get('Accept') or DEFAULT_ACCEPT_HEADER
    status = "OK"

    def envelope(headers={}, **kwargs) -> response.HTTPResponse:
        hdr = dict({
            RESPONSE_STATUS: status
        }, **headers)

        return json_response(dict({
            "_status": status,
        }, headers=hdr, **kwargs))

    if len(responses) == 0:
        return envelope()

    if not accept_hdr or accept_hdr == '*/*':
        accept_hdr = DEFAULT_ACCEPT_HEADER

    for accept_entry in accept_hdr.split(','):
        accept, _, _ = accept_entry.partition(';')
        accept = accept.strip().lower()

        # @TODO: Process paypload based on 'Accept' header
        if accept in ("json/array", "application/json+array"):
            return envelope(_resp=responses)

        if accept in ("application/json", "application/json+object"):
            return envelope(**{getattr(r, CQRS_ENTITY_KEY): r.data for r in responses})

        if accept in ("application/json+single", "json/object"):
            return envelope(**check_data_response(responses))

        if accept in ("text/plain", "text"):
            return response.text(check_text_response(responses))

    raise BadRequestError("L9012", f"Invalid accept header: {accept_hdr}")

