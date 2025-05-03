"""
    @TODO:
    - [ ] auth - Support private key client authorization
    - [ ] auth - Implement custom session backend (e.g. redis, etc.)
"""
from ._meta import config, logger
from .auth import setup_authentication, auth_required
from .setup import create_app, on_startup, on_shutdown
from .domain import configure_domain_manager
from .query import configure_query_manager

