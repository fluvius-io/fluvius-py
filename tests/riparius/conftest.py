
import json

from fluvius.data import UUID_GENF
from fluvius.fastapi.auth import FluviusAuthProfileProvider
from riparius import Workflow, Stage, Step, Role, st_connect, wf_connect, transition, FINISH_STATE

from typing import Optional
from httpx import AsyncClient
from fluvius.data.serializer.json_encoder import FluviusJSONEncoder
from fastapi import Request


st01 = UUID_GENF('100')
wf01 = UUID_GENF('101')




class SampleProcess(Workflow):
    ''' Sample workflow description ... '''

    class Meta:
        title = "Sample Process"
        revision = 1

    Stage01 = Stage('Stage 01', desc="Iam great")
    Stage02 = Stage('Stage 02', desc="Iam bigger")
    Role01 = Role(title="Role 01")

    def on_start(wf_state):
        step3 = wf_state.add_step('Step03', selector=st01)
        step3.transit('MOON')

    class Step01(Step, name='Step 03', stage=Stage01):
        """ This is a sample step. 2-X """
        pass

    class Step02(Step, name="step-02a", stage=Stage01):
        """ This is a sample step. 2-X """
        pass

    class Step02b(Step, stage=Stage01):
        """ This is a sample step. 2-B """
        __step_name__ = "Step2B"

    class Step03(Step, name="Step 03", stage=Stage01):
        __states__ = ('TAKE', 'ME', 'TO', 'THE', 'MOON')

        @st_connect('test-event')
        def test_event_step(state, event):
            state.memorize(test_step_key="value")
            s1 = state.add_step('Step02b', test_key_02="value")
            s2 = state.add_step('Step02', test_key_02=str(s1._id))
            state.transit('TAKE')
            s1.transit(FINISH_STATE)
            s2.transit(FINISH_STATE)
            assert state._id == s1._data.origin_step and s2._data.origin_step == state._id
            yield f"test_event_step ACTION! #2 {s1} & {s2} => {event}"
            yield f"MEMORY: {state.recall()}"

        @transition('TAKE')
        def to_TAKE(state, cur_state):
            yield f'TRANSITIONING TO TAKE: {state._id} => {cur_state}'

    @wf_connect('test-event')
    def test_event(workflow, trigger_data):
        workflow.memorize(test_key="workflow value 2")
        workflow.output(message='SUCCESS!')
        workflow.output(file='contract/contract-final-v2.pdf')
        yield f"test_event ACTION! #1: {trigger_data}"
        yield f"MEMORY: {workflow.recall()}"


class FluviusMockProfileProvider(FluviusAuthProfileProvider):
    TEMPLATE = {
        "exp": 1753419182,
        "iat": 1753418882,
        "auth_time": 1753418870,
        "jti": "1badb45d-34cd-42ba-8585-8ff5a5b707d3",
        "iss": "https://id.adaptive-bits.com/auth/realms/dev-1.fluvius.io",
        "aud": "sample_app",
        "sub": "44d2f8cb-0d46-4323-95b9-c5b4bdbf6205",
        "typ": "ID",
        "azp": "sample_app",
        "nonce": "Ggeg9O9qcHthA1idx8nE",
        "session_state": "8889f832-1d59-4886-8f08-1d613c793d38",
        "at_hash": "51a1KP4pfSKNiBA6K0Du1g",
        "acr": "0",
        "sid": "8889f832-1d59-4886-8f08-1d613c793d38",
        "email_verified": True,
        "name": "John Doe",
        "preferred_username": "johndoe",
        "given_name": "John",
        "family_name": "Doe",
        "email": "johndoe@adaptive-bits.com",
        "realm_access": {
            "roles": [
            "default-roles-dev-1.fluvius.io",
            "offline_access",
            "uma_authorization"
            ]
        },
        "resource_access": {
            "account": {
            "roles": ["manage-account", "manage-account-links", "view-profile"]
            }
        }
    }

    def get_auth_token(self, request: Request) -> Optional[str]:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("MockAuth "):
            raise ValueError("Invalid authorization header")

        try:
            data = json.loads(auth_header.split("MockAuth ")[1])
            return self.TEMPLATE | data
        except json.JSONDecodeError:
            raise ValueError("Invalid JSON in authorization header")


# Custom AsyncClient with FluviusJSONEncoder
class FluviusAsyncClient(AsyncClient):
    """AsyncClient that uses FluviusJSONEncoder for JSON serialization"""
    
    async def request(self, method, url, **kwargs):
        # If json data is provided, serialize it with FluviusJSONEncoder
        if 'json' in kwargs:
            kwargs['content'] = json.dumps(kwargs.pop('json'), cls=FluviusJSONEncoder)
            kwargs['headers'] = kwargs.get('headers') or {}
            kwargs['headers'].setdefault('Content-Type', 'application/json')
        
        return await super().request(method, url, **kwargs)

