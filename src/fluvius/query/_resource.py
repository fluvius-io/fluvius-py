import re
import json
from typing import Optional, List, Dict, Any, Tuple
from types import SimpleNamespace
from fluvius.error import BadRequestError
from fluvius.data import DataModel, BlankModel
from fluvius.helper import assert_
from fluvius.data.query import operator_statement, OperatorStatement, QueryStatement, process_query_statement
from fluvius.constant import DEFAULT_DELETED_FIELD, QUERY_OPERATOR_SEP, OPERATOR_SEP_NEGATE, RX_PARAM_SPLIT
from pydantic import BaseModel, Field

from . import logger, config

DEVELOPER_MODE = config.DEVELOPER_MODE


def endpoint(url):
    def decorator(func):
        func.__custom_endpoint__ = (url, func)
        return func

    return decorator


class QueryResourceMeta(DataModel):
    name: str
    desc: Optional[str] = None
    tags: Optional[List] = None

    backend_model: Optional[str] = None

    allow_item_view: bool = True
    allow_list_view: bool = True
    allow_meta_view: bool = True
    auth_required: bool = True

    scope_required: Optional[Dict] = None
    scope_optional: Optional[Dict] = None

    soft_delete_query: Optional[str] = DEFAULT_DELETED_FIELD

    ignored_params: List = tuple()
    default_order: List = tuple()
    select_all: bool = False

    policy_required: bool = False


from .base import QueryResource
