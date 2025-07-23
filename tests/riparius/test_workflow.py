import asyncio
import pytest
from pprint import pformat
from types import SimpleNamespace
from riparius import logger, config
from riparius import Workflow, Stage, Step, Role, st_connect, wf_connect, transition, FINISH_STATE, ActivityRouter, WorkflowManager
from fluvius.data import UUID_GENF


st01 = UUID_GENF('100')
wf01 = UUID_GENF('101')


class SampleProcess(Workflow):
    ''' Sample workflow description ... '''

    class Meta:
        title = "Sample Process"
        revision = 1

    Stage01 = Stage('Stage 01')
    Stage02 = Stage('Stage 02')
    Role01 = Role(title="Role 01")

    def on_start(wf_state):
        step3 = wf_state.add_step('Step03', selector=st01)
        step3.transit('MOON')

    class Step01(Step, name='Step 03', stage=Stage01):
        pass

    class Step02(Step, name="step-02a", stage=Stage01):
        pass

    class Step02b(Step, stage=Stage01):
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
        yield f"test_event ACTION! #1: {trigger_data}"
        yield f"MEMORY: {workflow.recall()}"


@pytest.mark.asyncio
async def test_workflow():
    manager = WorkflowManager()
    evt_data = SimpleNamespace(workflow_id=wf01, step_id=st01)
    for wf in manager.process_activity('test-event', evt_data):
        assert len(wf.step_id_map) == 3  # 3 steps created
        mutations, messages, events = await manager.persist(wf)


