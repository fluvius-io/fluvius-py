import os
import re
import json
import jinja2
import jsonurl_py
from time import time
from typing import List, Dict, Any, Set
from casbin import Model
from casbin.persist.adapters.asyncio import AsyncAdapter

from .enforcer import FluviusEnforcer
from .adapter import SqlAdapter
from .datadef import (
    PolicyRequest, PolicyResponse, PolicyData, PolicyNarration, PolicyMeta,
    PolicyScope, ConditionNode, ConditionLeaf
)
from fluvius.error import ForbiddenError
from ._meta import config, logger
from fluvius.error import BadRequestError, ForbiddenError

DEFAULT_CASBIN_TABLE = 'casbin_rule'


class PolicyManager:
    """Policy manager using Casbin for access control."""

    __adapter__ = SqlAdapter
    __model__ = None
    __schema__ = DEFAULT_CASBIN_TABLE

    def __init_subclass__(cls):
        if not cls.__model__:
            base_path = os.path.dirname(os.path.abspath(__file__))
            cls.__model__ = os.path.join(base_path, config.CASBIN_MODEL_PATH)

        if not cls.__adapter__:
            raise BadRequestError("C00.201", "[__adapter__] is required! e.g. `policy.csv` or `SqlAdapter`. etc.")

    def __init__(self, dam=None):
        self._dam = dam
        self._adapter = None
        self._enforcer = None
        self._model = None
        self._jinja = jinja2.Environment(undefined=jinja2.StrictUndefined)

        self._setup_model()
        self._setup_adapter()
        self._setup_enforcer()

    def _setup_model(self):
        """Setup the Casbin model."""
        self._model = Model()
        self._model.load_model(self.__model__)

    def _setup_adapter(self):
        """Setup the policy storage adapter."""
        if issubclass(self.__adapter__, (AsyncAdapter)):
            if not self.__schema__:
                raise BadRequestError("C00.202", "[__schema__ is required for Custom like SQLAdapter.]")
            self._adapter = self.__adapter__(self._dam, self.__schema__)
        else:
            self._adapter = self.__adapter__

    def _setup_enforcer(self):
        self._enforcer = FluviusEnforcer(self._model, self._adapter)

    def _get_filter_from_request(self, request: PolicyRequest):
        """Get the filter from the request."""
        return self._adapter.get_filter_from_request(request)

    async def check_permission(self, request: PolicyRequest) -> PolicyResponse:
        try:
            fitler = self._get_filter_from_request(request)
            await self._enforcer.load_filtered_policy(fitler)
            allowed, narration, trace = self._enforcer.enforce_ex(
                request.usr,
                request.pro,
                request.org,
                request.rid,
                request.cqrs,
                request.act,
            )
            narration_obj = await self._generate_narration(request, allowed, narration, trace)
            return PolicyResponse(
                allowed=allowed,
                narration=narration_obj
            )
        except Exception as e:
            raise ForbiddenError("C00.203", f"Permission check failed: {str(e)}", str(e))

    async def _generate_narration(self, request: PolicyRequest, allowed: bool, narration: list, trace: list) -> PolicyNarration:
        """Generate a human readable explanation of the policy decision."""
        policies = []
        if narration:
            for policy in narration:
                prule = PolicyData(
                    role=policy[0],
                    act=policy[1],
                    cqrs=policy[2],
                    meta=policy[3],
                    scope=policy[4],
                )
                policies.append(prule)

        restriction = {}
        if request.cqrs == "QUERY":
            restriction = await self._generate_restriction(request, policies) if policies else {}

        return PolicyNarration(policies=policies, trace=trace, restriction=restriction)

    async def _generate_restriction(self, request: PolicyRequest, policies: List[PolicyData]) -> dict:
        if not policies:
            return {}
        
        context      = self._build_context(request)
        scope, metas = self._reconcile_policies(policies)
        conditions   = self._reconcile_condition(scope, metas, context)

        return conditions.to_query_statement()

    def _parse_meta(self, policies: List[PolicyData]) -> List[PolicyMeta]:
        """Parse the metas from the policies."""
        parsed_metas = []
        for policy in policies:
            if not policy.meta:
                continue

            try:
                meta_dict = jsonurl_py.loads(policy.meta)
                meta = PolicyMeta(**meta_dict)
                parsed_metas.append(meta)
            except (jsonurl_py.ParseError, KeyError, ValueError) as e:
                raise BadRequestError('C00.204', f'Failed to parse policy meta: {policy.meta}, error: {e}')

        return parsed_metas

    def _reconcile_policies(self, policies: List[PolicyData]) -> List[PolicyData]:
        scope = self._reconcile_scope(policies)
        policies = [policy for policy in policies if policy.scope == scope]
        return scope, self._parse_meta(policies)

    def _reconcile_scope(self, policies: List[PolicyData]) -> PolicyScope:
        if not policies:
            return PolicyScope.SYSTEM

        scopes = [policy.scope for policy in policies]
        if PolicyScope.SYSTEM in scopes:
            return PolicyScope.SYSTEM
        
        if PolicyScope.TENANT in scopes:
            return PolicyScope.TENANT
        
        if PolicyScope.DOMAIN in scopes:
            return PolicyScope.DOMAIN
        
        return PolicyScope.SYSTEM

    def _retrieve_resource(self, request: PolicyRequest) -> Dict[str, Set[str]]:
        return set(rule[2] for rule in self._enforcer.get_filtered_named_grouping_policy("g3", 0, request.pro))

    def _build_context(self, request: PolicyRequest) -> Dict[str, Any]:
        res_ids = self._retrieve_resource(request)
        return {
            "request": request.model_dump(),
            "restriction": {
                "org": request.org,
                "resource_ids": list(res_ids),
            }
        }

    def _reconcile_condition(self, scope: PolicyScope, metas: List[PolicyMeta], context: Dict[str, Any]) -> ConditionNode:
        if not metas:
            return ConditionNode()

        final_condition = []

        for meta in metas:
            ctx = context.copy()
            meta_cond = meta.restriction.condition
            if not meta_cond:
                continue
            
            scope_cond = getattr(meta_cond, scope, None)
            if not scope_cond:
                continue

            rendered = self._render_condition(scope_cond, ctx)
            has_all = hasattr(rendered, 'ALL') and rendered.ALL and len(rendered.ALL) > 0
            has_any = hasattr(rendered, 'ANY') and rendered.ANY and len(rendered.ANY) > 0
            if has_all or has_any:
                final_condition.append(rendered)

        if not final_condition:
            return ConditionNode()

        return ConditionNode(ALL=final_condition)

    def _render_condition(self, condition: ConditionNode, context: Dict[str, Any]) -> ConditionNode:
        if not condition:
            return ConditionNode()

        def _render_leaf(leaf: ConditionLeaf) -> ConditionLeaf:
            return ConditionLeaf(
                field=leaf.field,
                op=leaf.op,
                value=self._render_value(leaf.value, context)
            )
        
        def _render_node(node: ConditionNode) -> ConditionNode:
            result = ConditionNode()
            
            if node.ALL:
                result.ALL = [
                    _render_leaf(item) if isinstance(item, ConditionLeaf) else _render_node(item)
                    for item in node.ALL
                ]
            
            if node.ANY:
                result.ANY = [
                    _render_leaf(item) if isinstance(item, ConditionLeaf) else _render_node(item)
                    for item in node.ANY
                ]
            
            return result
        
        return _render_node(condition)
        
    def _render_value(self, val: str, context: Dict[str, Any]) -> Any:
        try:
            if isinstance(val, str):
                context_matched = re.match(r"^context\((.*?)\)$", val.replace(" ", ""))
                if context_matched:
                    path = context_matched.group(1)
                    parts = path.split(".")
                    result = context
                    for part in parts:
                        result = result[part]
                    return result
            return val
        except Exception as e:
            raise BadRequestError('C00.205', f"Failed to render value: {val}, error: {e}")