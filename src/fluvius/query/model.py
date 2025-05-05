from fluvius.data import DataModel
from typing import Optional, List, Dict, Any, Tuple
from fluvius.data.query import OperatorStatement
from . import config


class FrontendQuery(DataModel):
    size: int = config.DEFAULT_QUERY_LIMIT
    page: int = 1

    select: Optional[List[str]] = None
    deselect: Optional[List[str]] = None

    sort: Optional[List[str]] = None
    query: Optional[str] = None

