import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from typing import List, Any, Dict
from casbin.persist.adapters.asyncio import AsyncAdapter
from casbin.model import Model
from casbin import persist


class PolicySchema:
    _id = sa.Column(UUID, primary_key=True, nullable=False)
    ptype = sa.Column(sa.String(255))
    v0 = sa.Column(sa.String(255))
    v1 = sa.Column(sa.String(255))
    v2 = sa.Column(sa.String(255))
    v3 = sa.Column(sa.String(255))
    v4 = sa.Column(sa.String(255))
    v5 = sa.Column(sa.String(255))

    _deleted = sa.Column(sa.DateTime)


class SqlAdapter(AsyncAdapter):
    """SQL adapter for Casbin that uses Fluvius data driver."""
    
    def __init__(self, manager, table):
        self._manager = manager
        self._table = table

    async def load_policy(self, model: Model) -> None:
        """Load all policies from database."""
        policies = await self._manager.find_all(self._table)
        for policy in policies:
            self._load_policy_line(policy, model)

    async def load_filtered_policy(self, model: Model, filter_: Dict[str, Any]) -> None:
        """Load filtered policies from database."""
        policies = self._manager.find_all(self._table, **filter_)
        for policy in policies:
            self._load_policy_line(policy, model)

    def _load_policy_line(self, policy: Any, model: Model) -> None:
        """Load a policy line into the model."""
        values = [
            policy.ptype,
            policy.v0,
            policy.v1,
            policy.v2,
            policy.v3,
            policy.v4,
            policy.v5
        ]
        values = [str(v) for v in values if v is not None]
        persist.load_policy_line(", ".join(values), model)

    def is_filtered(self) -> bool:
        """Return true since this adapter supports policy filtering."""
        # return True
        return False

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