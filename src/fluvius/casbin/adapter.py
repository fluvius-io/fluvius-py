import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from typing import List, Any, Dict
from casbin.persist.adapters.asyncio import AsyncAdapter
from casbin.model import Model
from casbin import persist

from .datadef import PolicyRequest
from fluvius.error import BadRequestError
from ._meta import logger


MAX_POLICY_LINE = 10000


class PolicySchema:
    _id = sa.Column(UUID, primary_key=True, nullable=False)
    ptype = sa.Column(sa.String(255))
    role = sa.Column(sa.String(255))
    usr = sa.Column(sa.String(255))
    pro = sa.Column(sa.String(255))
    org = sa.Column(sa.String(255))
    rid = sa.Column(sa.String(255))
    act = sa.Column(sa.String(255))
    cqrs = sa.Column(sa.String(255))
    meta = sa.Column(sa.TEXT)
    scope = sa.Column(sa.String(255))

    _deleted = sa.Column(sa.DateTime)

    @classmethod
    def format_policy(cls, p):
        ptype = p.ptype
        match ptype:
            case "p":
                return [ptype, p.role, p.act, p.cqrs, p.meta, p.scope]
            case "g":
                return [ptype, p.usr, p.pro, p.org]
            case "g2":
                return [ptype, p.pro, p.role]
            case "g3":
                return [ptype, p.pro, p.role, p.rid]
            case _:
                raise BadRequestError("C00.301", f"Unsupported policy type: {ptype}")

    @classmethod
    def get_filter_from_request(cls, request: PolicyRequest):
        """Get the filter from the request."""
        return {
            ".or": [
                {
                    ".and": [{
                        "ptype": "p",
                        "act": request.act,
                        "cqrs": request.cqrs,
                    }]
                },
                {
                    ".and": [{
                        "ptype": "g",
                        "usr": str(request.auth_ctx.user.id),
                        "pro": str(request.auth_ctx.profile.id),
                        "org": str(request.auth_ctx.organization.id),
                    }]
                },
                {
                    ".and": [{
                        "ptype": "g2",
                        "pro": str(request.auth_ctx.profile.id),
                    }]
                },
                {
                    ".and": [{
                        "ptype": "g3",
                        "pro": str(request.auth_ctx.profile.id),
                    }]
                }
            ]
        }
    

class SqlAdapter(AsyncAdapter):
    """SQL adapter for Casbin that uses Fluvius data driver."""
    def __init__(self, manager, schema):
        self._manager = manager
        self._schema = schema
        self._table = schema.__tablename__

    def get_filter_from_request(self, request: PolicyRequest) -> Dict[str, Any]:
        """Get the filter from the request."""
        return self._schema.get_filter_from_request(request)

    async def load_policy(self, model: Model) -> None:
        """Load all policies from database."""
        policies = await self._manager.query(self._table, limit=MAX_POLICY_LINE)
        for policy in policies:
            self._load_policy_line(policy, model)

    async def load_filtered_policy(self, model: Model, filter_: Dict[str, Any]) -> None:
        """Load filtered policies from database."""
        policies = await self._manager.query(self._table, limit=MAX_POLICY_LINE, where=filter_)
        for policy in policies:
            self._load_policy_line(policy, model)

    def _load_policy_line(self, policy: Any, model: Model) -> None:
        """Load a policy line into the model."""
        values = self._schema.format_policy(policy)
        values = [str(v) for v in values if v is not None]
        logger.info(f'Load policy line: {values}')
        persist.load_policy_line(", ".join(values), model)

    def is_filtered(self) -> bool:
        """Return true since this adapter supports policy filtering."""
        return True

    async def save_policy(self, model: Model) -> bool:
        """Not implemented as this is a read-only adapter."""
        raise NotImplementedError("This PolicyManager is read-only")

    async def add_policy(self, sec: str, ptype: str, rule: List[str]) -> None:
        """Not implemented as this is a read-only adapter."""
        raise NotImplementedError("This PolicyManager is read-only")

    async def remove_policy(self, sec: str, ptype: str, rule: List[str]) -> None:
        """Not implemented as this is a read-only adapter."""
        raise NotImplementedError("This PolicyManager is read-only")

    async def remove_filtered_policy(
        self, sec: str, ptype: str, field_index: int, *field_values: List[str]
    ) -> None:
        """Not implemented as this is a read-only adapter."""
        raise NotImplementedError("This PolicyManager is read-only") 
