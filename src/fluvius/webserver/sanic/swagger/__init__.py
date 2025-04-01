from .cfg import config, logger


def configure_sanic_swagger(app):
    if app.config.get('ENABLE_OPENAPI_DOCS'):
        from . import swagger
        app.blueprint(swagger.get_swagger_blueprint(app))

    return app


__all__ = ('config', 'logger')
__version__ = "1.0.0"
