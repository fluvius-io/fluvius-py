from .cfg import config, logger
from . import toolbelt

__all__ = ('config', 'logger', 'configure_toolbox')
__version__ = "1.0.0"


def configure_toolbox(app):
    toolbelt.setup_app(app)
    logger.info('/SENTRY/ Configured Sanic Toolbox')
    return app
