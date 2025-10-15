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
    limit: int = Field(description="Page size. Maximum returned items.", default=config.DEFAULT_QUERY_LIMIT)
    page: int = Field(description="Page number.", default=1)

    include: str | None = Field(description="Fields to be included in the result. Empty to include all fields. Comma separated.", default=None)
    exclude: str | None = Field(description="Fields to be excluded from the result. Comma separated. E.g. `id,name,desc`", default=None)
    sort: str | None = Field(description="Comma separated sort order. E.g. `sort=created.asc,name.desc`", default=None)
    query: str | None = Field(description="Conditional query. URL encoded JSON. E.g. `query={\"name.eq\":\"Harry\"}`", default=None)

    text: str | None = Field(description="Search query. E.g. `text=Harry`", default=None)

class FrontendQuery(DataModel):
    limit: int = config.DEFAULT_QUERY_LIMIT
    page: int = 1

    include: Optional[List[str]] = None
    exclude: Optional[List[str]] = None
    sort: Optional[List[str]] = None
    user_query: Optional[Dict] = None
    path_query: Optional[Dict] = None
    scope: Optional[Dict] = None
    text: Optional[str] = None

    @classmethod
    def from_query_params(cls, qp: QueryParams, /, path_query=None, scope=None, scope_schema=None):
        return cls(
            limit=qp.limit,
            page=qp.page,
            include=SELECT_DECODER(qp.include),
            exclude=SELECT_DECODER(qp.exclude),
            sort=SORT_DECODER(qp.sort),
            user_query=QUERY_DECODER(qp.query),
            path_query=PATH_DECODER(path_query),
            scope=SCOPE_DECODER(scope, scope_schema),
            text=qp.text,
        )


class QueryResourceMeta(DataModel):  # We need DataModel.create method
    name: str
    desc: Optional[str] = None
    tags: Optional[List] = None

    resource: str = None
    backend_model: Optional[str] = None

    allow_item_view: bool = True
    allow_list_view: bool = True
    allow_meta_view: bool = True
    allow_text_search: bool = False
    allow_path_query: bool = False

    strict_response: bool = False
    auth_required: bool = True

    scope_required: Optional[Type[BaseModel]] = None
    scope_optional: Optional[Type[BaseModel]] = None

    soft_delete_query: Optional[str] = DEFAULT_DELETED_FIELD

    ignored_params: List = tuple()
    default_order: List = tuple()
    include_all: bool = False
    excluded_fields: List = tuple()

    policy_required: str = None
