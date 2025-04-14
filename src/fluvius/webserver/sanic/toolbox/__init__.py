from .cfg import config, logger
from . import toolbelt

__all__ = ('config', 'logger', 'configure_toolbox')

def configure_toolbox(app):
    toolbelt.setup_app(app)
    logger.info('/SENTRY/ Configured Sanic Toolbox')
    return app
