from pydantic import BaseModel, Field

from fluvius.data import DataModel
from fluvius.data.query import OperatorStatement
from fluvius.error import BadRequestError
from fluvius.constant import DEFAULT_DELETED_FIELD

from typing import Optional, List, Dict, Any, Tuple, Union, Type

from .helper import json_decoder, jurl_decoder, list_decoder, scope_decoder

from . import config

QUERY_DECODER = json_decoder
PATH_DECODER = jurl_decoder
SELECT_DECODER = list_decoder
SORT_DECODER = list_decoder
SCOPE_DECODER = scope_decoder


class QueryParams(DataModel):
    limit: int = config.DEFAULT_QUERY_LIMIT
    page: int = 1

    select: Optional[str] = None
    sort: Optional[str] = None
    query: Optional[str] = None


class FrontendQuery(DataModel):
    limit: int = config.DEFAULT_QUERY_LIMIT
    page: int = 1

    select: Optional[List[str]] = None
    sort: Optional[List[str]] = None
    user_query: Optional[Dict] = None
    path_query: Optional[Dict] = None
    scope: Optional[Dict] = None

    @classmethod
    def from_query_params(cls, qp: QueryParams, /, path_query=None, scope=None, scope_schema=None):
        return cls(
            limit=qp.limit,
            page=qp.page,
            select=SELECT_DECODER(qp.select),
            sort=SORT_DECODER(qp.sort),
            user_query=QUERY_DECODER(qp.query),
            path_query=PATH_DECODER(path_query),
            scope=SCOPE_DECODER(scope, scope_schema),
        )


class QueryResourceMeta(DataModel):  # We need DataModel.create method
    name: str
    desc: Optional[str] = None
    tags: Optional[List] = None

    backend_model: Optional[str] = None

    allow_item_view: bool = True
    allow_list_view: bool = True
    allow_meta_view: bool = True
    strict_response: bool = False
    auth_required: bool = True

    scope_required: Optional[Type[BaseModel]] = None
    scope_optional: Optional[Type[BaseModel]] = None

    soft_delete_query: Optional[str] = DEFAULT_DELETED_FIELD

    ignored_params: List = tuple()
    default_order: List = tuple()
    select_all: bool = False

    policy_required: bool = False
