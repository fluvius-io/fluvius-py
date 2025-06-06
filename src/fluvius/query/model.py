from fluvius.data import DataModel, Field
from typing import Optional, List, Dict, Any, Tuple, Union
from fluvius.data.query import OperatorStatement
from fluvius.error import BadRequestError
from . import config


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
    query: Optional[str] = Field(alias='q')


class FrontendQuery(DataModel):
    limit: int = config.DEFAULT_QUERY_LIMIT
    page: int = 1

    select: Optional[List[str]] = None
    sort: Optional[List[str]] = None
    user_query: Optional[Dict] = None
    path_query: Optional[Dict] = None
    scopes: Optional[Dict] = None


    def from_query_params(qp: QueryParams, /, **kwargs) -> FrontendQuery:
        return FrontendQuery(
            limit=qp.limit,
            page=qp.page,
            select=parse_list(qp.select),
            sort=parse_list(qp.sort),
            user_query=parse_json(qp.query),
            **kwargs
        )
