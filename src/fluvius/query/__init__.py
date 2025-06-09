'''

See: https://github.com/dialoguemd/fastapi-sqla/
'''

from ._meta import config, logger
from .model import QueryParams, FrontendQuery
from .resource import QueryResource, QueryResourceMeta, endpoint
from .manager import QueryManager, DomainQueryManager
from .loader import (
    load_query_resources_from_file,
    load_query_resources_from_directory,
    create_sample_config,
    save_sample_config,
    QueryResourceSpec
)

__all__ = (
    "DomainQueryManager",
    "FrontendQuery",
    "QueryManager",
    "QueryParams",
    "QueryResource",
    "QueryResourceMeta",
    "QueryResourceSpec",
    "config",
    "endpoint",
    "load_query_resources_from_file",
    "load_query_resources_from_directory",
    "create_sample_config",
    "save_sample_config",
    "logger",
)
