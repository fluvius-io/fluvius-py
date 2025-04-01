import json
import os
import tempfile

from fluvius.domain.decorators import domain_entity_registry
from fluvius.domain.entity import DomainEntityType
from mdutils import MdUtils
from fluvius_query.registry import get_resource, resource_items

from sanic_swagger import config

CQRS_PAYLOAD_FIELD = "data"
QUERY_EMBED_PREFIX = "embed"
OPENAPI_TYPE_MAPPING = {
    "bool": {"type": "boolean"},
    "date": {"type": "string", "format": "date"},
    "datetime": {"type": "string", "format": "date-time"},
    "int": {"type": "string", "format": "string"},
    "integer": {"type": "string", "format": "string"},
    "list": {"type": "string"},
    "str": {"type": "string", "format": "string"},
    "UUID": {"type": "string", "format": "uuid"},
    "dict": {"type": "object", "format": "json"},
}

OPENAPI_TYPE_DEFAULT = {"type": "string", "format": "string"}


def type_mapping(_type):
    ''' Note: be careful not to modify the result returned by this method.
        We do not want to do a copy here for performance sake. '''
    return OPENAPI_TYPE_MAPPING.get(_type, OPENAPI_TYPE_DEFAULT)


def generate_payload_schema(datadef):
    '''
    class A(PClass):
       name = field(str)
       age = field(type=(str, type(None)))
       class Meta:
            descriptions = {
                'name': 'Your full name',
                'age': 'Your age',
            }
            examples = {
                "name": "John Doe",
                "age": 10
            }
    return {
        "application/json": {
            "schema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "format": "string",
                        "description": "Your full name",
                        "age": "John Doe"
                    },
                    "age": {
                        "type": "string",
                        "format": "string",
                        "description": "Your age",
                        "age": 10
                    }
                }
            }
        }
    }
    '''

    attributes = datadef._pclass_fields

    descriptions = {}
    examples = {}

    if hasattr(datadef, "Meta"):
        descriptions = getattr(datadef.Meta, "descriptions", {})
        examples = getattr(datadef.Meta, "examples", {})

    def _gen():
        for field, field_def in attributes.items():
            for field_type in field_def.type:
                if field_type == type(None):  # noqa
                    continue

                fieldmeta = {}
                fieldmeta.update(type_mapping(field_type.__name__))
                fieldmeta["description"] = descriptions.get(field)
                fieldmeta["example"] = examples.get(field)

                yield (field, fieldmeta)

    return {
        "application/json": {
            "schema": {
                "type": "object",
                "properties": dict(_gen())
            }
        }
    }


def generate_command_spec(url, schema, description, tags, parameters):
    spec = {
        "summary": description or url,
        "description": f"POST {url}",
        "tags": tags,
        "responses": {
            "200": {
                "description": "OK",
            }
        }
    }

    if parameters is not None:
        spec["parameters"] = parameters

    if schema is not None:
        spec["requestBody"] = {
            "required": True,
            "content": schema
        }

    return spec


def generate_command_api():
    '''
    command class should look like:
        class CreateCredentialPackage(Command):
            data = field(type=CredentialPackageData, mandatory=True)

            class Meta:
                resource = "credential-package"
                tags = ["package"]
                description = "Create new credential-package"
    '''

    for (key, kind, namespace), entity_cls in domain_entity_registry():
        if kind != DomainEntityType.COMMAND:
            continue

        payload_field = entity_cls._pclass_fields[CQRS_PAYLOAD_FIELD]
        schema = None
        description = None
        resource = "<resource>"
        tags = None
        parameters = None

        for type_cls in payload_field.type:
            # find PClass-inherited class type to enumerate payload
            if type_cls != type(None) and type_cls != dict:  # noqa
                schema = generate_payload_schema(type_cls)

        if hasattr(entity_cls, "Meta"):
            meta = entity_cls.Meta
            resource = getattr(meta, "resource", None)
            tags = getattr(meta, "tags", None)
            description = entity_cls.__doc__ or getattr(meta, "description", None)
            parameters = getattr(meta, "parameters", None)

        url = f"/{namespace}:{key}/{resource}"
        spec = generate_command_spec(url, schema, description, tags, parameters)

        yield (url, {"post": spec})


def generate_response_schema(url_prefix, query_cls, response_type):
    try:
        field_annotation = query_cls.Meta.field_annotation
    except AttributeError:
        field_annotation = dict()

    def array_schema_wrapper(props):
        return {
            "type": "array",
            "items": {
                "type": "object",
                "properties": props
            }
        }

    def object_schema_wrapper(props):
        return {
            "type": "object",
            "properties": props
        }

    def gen_schema(field_map, annotation):
        for field_key, field_def in field_map.items():
            if getattr(field_def, "hidden"):
                continue

            if field_def.datatype.startswith(QUERY_EMBED_PREFIX):
                embed_cls = get_resource(url_prefix, field_def.source)
                prop = generate_response_schema(url_prefix, embed_cls, response_type="array")
            else:
                prop = {
                    "description": annotation.get(field_key) or field_def.label,
                }
                prop.update(type_mapping(field_def.datatype))

            yield (field_key, prop)

    schema = dict(gen_schema(query_cls.__fieldmap__, field_annotation))
    schema_wrapper = array_schema_wrapper if response_type == "array" else object_schema_wrapper

    return schema_wrapper(schema)


def generate_item_spec(url, schema, description=None, tags=None, parameters=None):
    spec = {
        "summary": f"{description or url} (item view)",
        "description": f"GET {url}",
        "parameters": [
            {
                "name": "id",
                "in": "path",
                "description": "id of the item",
                "required": True,
                "schema": {
                    "type": "string",
                }
            }
        ],
        "tags": tags,
        "responses": {
            "200": {
                "description": "OK",
                "content": {
                    "application/json": {
                        "schema": schema
                    }
                }
            }
        }
    }

    if parameters is not None:
        spec["parameters"] += parameters

    return spec


def generate_array_spec(url, schema, description=None, tags=None, parameters=None):
    spec = {
        "summary": f"{description or url} (resource view)",
        "description": f"GET {url}",
        "tags": tags,
        "responses": {
            "200": {
                "description": "OK",
                "content": {
                    "application/json": {
                        "schema": schema
                    }
                }
            }
        }
    }

    if parameters is not None:
        spec["parameters"] = parameters
    return spec


def generate_query_api():
    for item in resource_items():
        (url_prefix, endpoint), query_cls = item

        # replace sanic syntax `<>` to open api syntax `{}`
        endpoint = endpoint.replace("<", "{").replace(">", "}")
        url = os.path.join("/", url_prefix, endpoint)

        tags = None
        description = None

        if hasattr(query_cls, "Meta"):
            meta = query_cls.Meta
            tags = getattr(meta, "tags", None)
            description = getattr(meta, "description", None)
            parameters = getattr(meta, "parameters", None)

        if getattr(query_cls, "__internal__", False):
            continue

        if not getattr(query_cls, "__disable_resource_view__", False):
            schema = generate_response_schema(url_prefix, query_cls, response_type="array")
            get_spec = generate_array_spec(url, schema, description, tags, parameters)

            yield (url, {"get": get_spec})

        if not getattr(query_cls, "__disable_item_view__", False):
            item_schema = generate_response_schema(url_prefix, query_cls, response_type="object")
            item_url = "%s/{id}" % (url)
            item_spec = generate_item_spec(item_url, item_schema, description, tags, parameters)

            yield (item_url, {"get": item_spec})


def format_single_object(data):
    props = data.get("properties")
    if props:
        return {
            key: format_array(value) if value.get("type") == "array" else value.get('type')
            for key, value in props.items()
        }

    if data.get("type") == "object":
        return None

    return data.get("type")


def format_array(data):
    return [format_single_object(data.get("items"))]


def format_resp(resp):
    if resp.get("type") == "object":
        return format_single_object(resp)

    return format_array(resp)


def json_paragraph(data):
    def run():
        yield "```json"
        yield json.dumps(
            data, sort_keys=True, indent=4, separators=(",", ": ")
        )
        yield "```"

    return "\n".join(run())


def init_md_file():
    _, temp_local_filename = tempfile.mkstemp()
    return MdUtils(file_name=temp_local_filename + ".md")


def generate_api_doc():
    md_file = init_md_file()
    md_file.new_header(level=1, title=config.OPENAPI_TITLE)

    md_file.new_header(2, "COMMAND")
    for index, (key, spec) in enumerate(generate_command_api(), 1):
        md_file.new_header(3, f'{index}. {spec["post"]["summary"]}')
        md_file.new_line(f'- POST `{key}`')
        request_spec = spec["post"].get("requestBody")

        if request_spec:
            payload_spec = request_spec["content"]["application/json"]["schema"]

            md_file.new_line("- Payload")
            md_file.new_paragraph(json_paragraph(format_resp(payload_spec)), wrap_width=0)

        md_file.new_line()

    md_file.new_header(2, "QUERY")
    for index, (key, spec) in enumerate(generate_query_api(), 1):
        md_file.new_header(3, f'{index}. {spec["get"]["summary"]}')
        md_file.new_line(f'- GET: `{key}`')
        response_spec = spec["get"].get("responses")

        if response_spec:
            response_payload = response_spec["200"]["content"]["application/json"]["schema"]

            md_file.new_line("- Response")
            md_file.new_paragraph(json_paragraph(format_resp(response_payload)), wrap_width=0)

        md_file.new_line()

    md_file.create_md_file()
    return md_file.file_name
