import json
import os

from sanic import Blueprint
from fluvius_oauth.blueprint import auth_required, login_required
from sanic.request import Request
from sanic.views import HTTPMethodView
from sanic_jinja2 import SanicJinja2

from fluvius.sanic.response import json_response
from fluvius_oauth.helper import oauth_error_handler
from . import config, logger

jinja = SanicJinja2()


def setup_blueprint(url_prefix):
    toolbelt = Blueprint('fluvius_toolbox', url_prefix=url_prefix)

    class AuthRequiredAsyncView(HTTPMethodView):
        decorators = [auth_required]

        async def get(self, request: Request, user):
            return json_response(user.serialize())

    class LoginRequiredAsyncView(HTTPMethodView):
        decorators = [login_required]

        async def get(self, request: Request, user):
            return json_response(user.serialize())

    @toolbelt.route('/')
    @jinja.template('toolbelt/index.html')
    async def dev_home(request):
        with open(config.LANDING_PAGE_API_MANIFEST) as f:
            api_list = json.load(f)

        return {
            'app_name': request.app.config.APPLICATION_NAME,
            'api_list': api_list
        }

    @toolbelt.route('/mqtt-test-notify')
    @oauth_error_handler
    @auth_required
    async def mqtt_test_notify(request, user):
        request.app.mqtt_notify(
            user_id=user.id,
            kind='mqtt-test-notify',
            target=user.id,
            msg=user.serialize()
        )
        return json_response(user.serialize())

    toolbelt.add_route(oauth_error_handler(LoginRequiredAsyncView.as_view()),
                       "/login-required")
    toolbelt.add_route(oauth_error_handler(AuthRequiredAsyncView.as_view()),
                       "/auth-required")

    return toolbelt


def setup_app(app):
    jinja.init_app(app, pkg_name='fluvius_toolbox', pkg_path='jinja2')
    if config.SETUP_MQTT_CLIENT:
        path = os.path.join(config.STATIC_PATH, 'mqtt_client')
        app.static(f'{config.TOOLBOX_PREFIX}/mqtt-client', path)

    if config.SETUP_UNAUTHORIZED_PAGE:
        @app.route('unauthorized/')
        @jinja.template('unauthorized/index.html')
        async def unauthorized_page(request):
            return {}

    toolbelt = setup_blueprint(config.TOOLBOX_PREFIX)
    logger.info('/TOOLBOX/ Setup done.')
    app.blueprint(toolbelt)
    return app


__all__ = None
