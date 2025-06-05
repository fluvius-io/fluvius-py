from fluvius.data import DataModel
from typing import Optional, List, Dict, Any, Tuple
from fluvius.data.query import OperatorStatement
from . import config


class FrontendQuery(DataModel):
    limit: int = config.DEFAULT_QUERY_LIMIT
    page: int = 1

    select: Optional[List[str]] = None
    sort: Optional[List[str]] = None
    query: Optional[str] = None

