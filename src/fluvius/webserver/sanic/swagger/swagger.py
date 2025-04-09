import os
import yaml

from fluvius.helper import load_yaml
from jinja2 import Environment, PackageLoader
from sanic.blueprints import Blueprint
from sanic.response import file, html, text

from .generator import (
    generate_api_doc,
    generate_command_api,
    generate_query_api
)


def get_swagger_blueprint(app):
    config = app.config

    swagger_blueprint = Blueprint(
        "swagger",
        url_prefix=f"/{config.OPENAPI_URL_PREFIX}/swagger")

    BASE_PATH = os.path.dirname(os.path.realpath(__file__))

    def resolve_path(rel_path):
        return os.path.join(BASE_PATH, rel_path)

    def load_manifest():
        manifest_file = config.OPENAPI_FILE_META if config.OPENAPI_FILE_META else \
            resolve_path("tmpl/openapi_default_header.yml")
        return load_yaml(manifest_file)

    @swagger_blueprint.route("/swagger.yml")
    def spec(request):
        def gen_spec():
            yield from generate_command_api()
            yield from generate_query_api()

        manifest = load_manifest()
        paths = manifest.get("paths", {}) or {}
        paths.update(gen_spec())

        manifest["paths"] = paths
        return text(yaml.dump(manifest))

    @swagger_blueprint.route('/index.html')
    async def bp_root(request):
        env = Environment(loader=PackageLoader('sanic_swagger', 'ui'))
        template = env.get_template('index.html')
        content = template.render(app_name=config.OPENAPI_TITLE)
        return html(content)

    @swagger_blueprint.route('/api.markdown')
    async def markdown(request):
        filepath = generate_api_doc()
        return await file(filepath)

    swagger_blueprint.static("/", resolve_path("ui"), strict_slashes=True)

    return swagger_blueprint
