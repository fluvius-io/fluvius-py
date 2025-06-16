import json
from fluvius.data import DataModel, Field
from typing import Optional, List, Dict, Any, Tuple, Union
from fluvius.data.query import OperatorStatement
from fluvius.error import BadRequestError
from . import config
from fluvius.constant import DEFAULT_DELETED_FIELD


def parse_list(value: Optional[str]) -> Optional[List[str]]:
    if not value:
        return None

    return [v.strip() for v in value.split(',') if v.strip()]


def parse_json(value: Optional[str]) -> Optional[Dict]:
    if not value:
        return None

    try:
        return json.loads(value)
    except json.JSONDecodeError as e:
        raise BadRequestError("Q101-503", "Invalid query value.", str(e))


class QueryParams(DataModel):
    limit: int = config.DEFAULT_QUERY_LIMIT
    page: int = 1

    select: Optional[str] = None
    sort: Optional[str] = None
    query: Optional[str] = Field(alias='q', default=None)


class FrontendQuery(DataModel):
    limit: int = config.DEFAULT_QUERY_LIMIT
    page: int = 1

    select: Optional[List[str]] = None
    sort: Optional[List[str]] = None
    user_query: Optional[Dict] = None
    path_query: Optional[Dict] = None
    scope: Optional[Dict] = None

    @classmethod
    def from_query_params(cls, qp: QueryParams, /, **kwargs):
        return cls(
            limit=qp.limit,
            page=qp.page,
            select=parse_list(qp.select),
            sort=parse_list(qp.sort),
            user_query=parse_json(qp.query),
            **kwargs
        )


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
