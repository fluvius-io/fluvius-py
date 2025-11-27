import os
from time import time
from casbin import Model
from casbin.persist.adapters.asyncio import AsyncAdapter

from .enforcer import FluviusEnforcer
from .adapter import SqlAdapter
from .datadef import PolicyRequest, PolicyResponse, PolicyData, PolicyNarration
from ._meta import config, logger


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
            raise ValueError("[__adapter__] is required! e.g. `policy.csv` or `SqlAdapter`. etc.")

    def __init__(self, dam=None):
        self._dam = dam
        self._adapter = None
        self._enforcer = None
        self._model = None

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
                raise ValueError("[__schema__ is required for Custom like SQLAdapter.]")
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
            start = time()
            await self._enforcer.load_filtered_policy(fitler)
            logger.info(f"Time taken to load filtered policy: {time() - start}")
            start = time()
            allowed, narration, trace = self._enforcer.enforce_ex(
                request.usr,
                request.pro,
                request.org,
                request.dom,
                request.res,
                request.rid,
                request.act,
                request.cqrs,
            )
            return PolicyResponse(
                allowed=allowed,
                narration=self._generate_narration(request, allowed, narration, trace)
            )
        except Exception as e:
            raise RuntimeError(f"Permission check failed: {str(e)}")

    def _generate_narration(self, request: PolicyRequest, allowed: bool, narration: list, trace: list) -> str:
        """Generate a human readable explanation of the policy decision."""
        message = f"Request: {request}"

        policies = []
        if narration:
            policies = []
            for policy in narration:
                print(policy)
                prule = PolicyData(
                    role=policy[0],
                    dom=policy[1],
                    res=policy[2],
                    act=policy[3],
                    cqrs=policy[4],
                    meta=policy[5],
                )
                policies.append(prule)

        return PolicyNarration(message=message, policies=policies, trace=trace)
