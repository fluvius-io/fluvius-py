
import json

from fluvius.data import UUID_GENF, logger
from fluvius.fastapi.auth import FluviusAuthProfileProvider
from fluvius.nava import Workflow, Stage, Step, Role, connect, transition, FINISH_STATE

from typing import Optional
from httpx import AsyncClient
from fluvius.data.serializer.json_encoder import FluviusJSONEncoder
from fastapi import Request

# Test Data
st01 = UUID_GENF('ST01')
wf01 = UUID_GENF('WF01')


class SampleProcess(Workflow):
    ''' Sample workflow description ... '''

    class Meta:
        title = "Sample Process"
        revision = 1

    Stage01 = Stage('Stage 01', desc="Iam great")
    Stage02 = Stage('Stage 02', desc="Iam bigger")
    Role01 = Role(title="Role 01")

    class Step01(Step, name='Step 03', stage=Stage01):
        """ This is a sample step. 2-X """
        pass

    class Step02(Step, name="step-02a", stage=Stage01, multiple=True):
        """ This is a sample step. 2-X """
        pass

    class Step02b(Step, stage=Stage01, multiple=True):
        """ This is a sample step. 2-B """
        __title__ = "Step2B"

    class Step03(Step, name="Step 03", stage=Stage01):
        __states__ = ('TAKE', 'ME', 'TO', 'THE', 'MOON')

        @transition('TAKE')
        def to_TAKE(state, cur_state):
            yield f'TRANSITIONING TO TAKE: {state._id} => {cur_state}'

        @connect('test-event', priority=100)
        def test_event_step(st_state, event):
            st_state.memorize(test_step_key="value")
            s1 = st_state.add_step('Step02b', test_key_02="value")
            s2 = st_state.add_step('Step02', test_key_02=str(s1._id))
            st_state.transit('TAKE')
            s1.transit(FINISH_STATE)
            s2.transit(FINISH_STATE)
            logger.warning('TEST EVENT 1')
            assert st_state._id == s1._data.src_step and s2._data.src_step == st_state._id
            yield f"test_event_step ACTION! #2 {s1} & {s2} => {event}"
            yield f"MEMORY: {st_state.recall()}"


    def on_start(wf_state):
        step3 = wf_state.add_step('Step03', selector=st01)
        step3.transit('MOON')

    @connect('test-event')
    def test_event(wf_state, event):
        wf_state.memorize(test_key="workflow value 2")
        wf_state.output(message='SUCCESS!')
        wf_state.output(file='contract/contract-final-v2.pdf')
        logger.warning('TEST EVENT 2')
        yield f"test_event ACTION! #1: {event}"
        yield f"MEMORY: {wf_state.recall()}"



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
