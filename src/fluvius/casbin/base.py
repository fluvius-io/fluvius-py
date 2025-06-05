from dataclasses import dataclass
from typing import List, Optional
from casbin import AsyncEnforcer, Model
from casbin.persist.adapters.asyncio import AsyncAdapter

from ._meta import config
from .adapter import SqlAdapter


DEFAULT_CASBIN_TABLE = 'casbin_rule'


@dataclass
class PolicyRequest:
    profile: str
    org: str
    domain: str
    action: str
    resource: str
    resource_id: str

@dataclass
class PolicyResponse:
    allowed: bool
    narration: str

@dataclass
class PolicyRule:
    role: str
    domain: str
    action: Optional[str] = None
    resource: Optional[str] = None
    resource_id: Optional[str] = None

class PolicyManager:
    """Policy manager using Casbin for access control."""

    __adapter__ = SqlAdapter
    __model__ = config.CASBIN_MODEL_PATH
    __table__ = DEFAULT_CASBIN_TABLE

    def __init_subclass__(cls):
        if not cls.__model__:
            raise ValueError("[__model__] is required! e.g. `model.conf`")

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
            if not self.__table__:
                raise ValueError("[__table__ is required for Custom like SQLAdapter.]")
            self._adapter = self.__adapter__(self._dam, self.__table__)
        else:
            self._adapter = self.__adapter__

    def _setup_enforcer(self):
        self._enforcer = AsyncEnforcer(self._model, self._adapter)

    async def check(self, *params) -> PolicyResponse:
        try:
            # @TODO: Need implement filtered policy for performance
            # await self.enforcer.load_filtered_policy()
            await self._enforcer.load_policy()
            allowed, narration = self._enforcer.enforce_ex(*params)
            return PolicyResponse(allowed=allowed, narration=narration)
        except Exception as e:
            raise RuntimeError(f"Permission check failed: {str(e)}")

    async def check_permission(self, request: PolicyRequest) -> PolicyResponse:
        # @TODO: Need implement filtered policy for performance
        # await self.enforcer.load_filtered_policy()
        try:
            allowed, narration = self._enforcer.enforce_ex(
                request.profile,
                request.org,
                request.domain,
                request.action,
                request.resource,
                request.resource_id
            )

            return PolicyResponse(
                allowed=allowed,
                narration=self._generate_narration(request, allowed, narration)
            )
        except Exception as e:
            raise RuntimeError(f"Permission check failed: {str(e)}")

    def _generate_narration(self, request: PolicyRequest, allowed: bool, narration: list) -> str:
        """Generate a human readable explanation of the policy decision."""
        status = "allowed" if allowed else "denied"
        return (
            f"Profile {request.profile} from organization {request.org} is {status} "
            f"to perform {request.action} on {request.resource}/{request.resource_id} "
            f"in domain {request.domain}"
        )

    async def get_roles(self, profile: str, org: str, domain: str) -> List[str]:
        """Get roles for a profile in an org and domain."""
        if not self._enforcer:
            raise RuntimeError("PolicyManager not initialized")
            
        return await self._enforcer.get_roles_for_user_in_domain(profile, domain)

    async def get_policies(self, role: str, domain: str) -> List[PolicyRule]:
        """Get policies for a role in a domain."""
        if not self._enforcer:
            raise RuntimeError("PolicyManager not initialized")

        policies = await self._enforcer.get_filtered_policy(0, role, domain)
        return [
            PolicyRule(
                role=policy[0],
                domain=policy[1],
                action=policy[2] if len(policy) > 2 else None,
                resource=policy[3] if len(policy) > 3 else None,
                resource_id=policy[4] if len(policy) > 4 else None
            )
            for policy in policies
        ] 