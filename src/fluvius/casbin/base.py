from pyrsistent import PClass, field
from casbin import AsyncEnforcer, Model
from casbin.persist.adapters.asyncio import AsyncAdapter

from ._meta import config
from .adapter import SqlAdapter


DEFAULT_CASBIN_TABLE = 'casbin_rule'


class PolicyRequest(PClass):
    sub = field(type=str, factory=str)
    org = field(type=str, factory=str)
    dom = field(type=str, factory=str)
    res = field(type=str, factory=str)
    rid = field(type=str, factory=str)
    act = field(type=str, factory=str)


class PolicyResponse(PClass):
    allowed = field(type=bool, factory=bool)
    narration = field(type=str, factory=str)


class PolicyManager:
    """Policy manager using Casbin for access control."""

    __adapter__ = SqlAdapter
    __model__ = config.CASBIN_MODEL_PATH
    __schema__ = DEFAULT_CASBIN_TABLE

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
            if not self.__schema__:
                raise ValueError("[__schema__ is required for Custom like SQLAdapter.]")
            self._adapter = self.__adapter__(self._dam, self.__schema__)
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
        try:
            # @TODO: Need implement filtered policy for performance
            # await self.enforcer.load_filtered_policy()
            await self._enforcer.load_policy()
            allowed, narration = self._enforcer.enforce_ex(
                request.sub,
                request.org,
                request.dom,
                request.res,
                request.rid,
                request.act,
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
            f"Sub {request.sub} from organization {request.org} is {status} "
            f"to perform {request.act} on {request.res}/{request.rid} "
            f"in doman {request.dom}"
        )
