from ._meta import config, logger
from .auth import setup_authentication, auth_required
from .setup import create_app, on_startup, on_shutdown
