import pytest
from pprint import pformat
from types import SimpleNamespace
from fluvius.process import logger, config
from fluvius.process.workflow import *
from fluvius.process.router import EventRouter
from fluvius.process.manager import WorkflowManager
from fluvius.data import UUID_GENF

st01 = UUID_GENF('100')
wf01 = UUID_GENF('101')



def test_workflow():

    class SampleProcess(Workflow, title='Sample Process', revision=1):
        ''' Sample workflow description ... '''

        Stage01 = Stage(title='Stage 01')
        Role01 = Role(title="Role 01")

        def on_started(wf_state, wf_params):
            step3 = wf_state.add_step('Step03', selector=st01)
            step3.transit('MOON')

        class Step01(Step, title='Step 03', stage=Stage01):
            pass

        class Step02(Step, title="step-02a", stage=Stage01):
            pass

        class Step02b(Step, stage=Stage01):
            __title__ = "Step2B"


        class Step03(Step, title="Step 03", stage=Stage01):
            __labels__ = ('TAKE', 'ME', 'TO', 'THE', 'MOON')

            @st_connect('test-event')
            def test_event_step(step, event):
                step.memorize(test_step_key="value")
                s1 = step.add_step('Step02b', test_key_02="value")
                s2 = step.add_step('Step02', test_key_02=str(s1._id))
                step.transit('TAKE')
                s1.transit('RUNNING')
                s2.transit('RUNNING')
                assert step._id == s1._data.src_step_id and s2._data.src_step_id == step._id
                yield f"test_event_step ACTION! #2 {s1} & {s2}"
                yield f"{step.memory()}"

            @transition('TAKE')
            def to_TAKE(step, cur_state):
                logger.info('TRANSITIONING TO TAKE: %s', step._id)

        @wf_connect('test-event')
        def test_event(workflow, event):
            workflow.memorize(test_key="workflow value 2")
            yield "test_event ACTION! #1"
            yield f"{workflow.memory()}"

    logger.info(EventRouter.ROUTING_TABLE)
    manager = WorkflowManager()
    evt_data = SimpleNamespace(workflow_id=wf01, step_id=st01)
    wf = manager.process_event('test-event', evt_data)[0]
    assert len(wf._steps) == 3
    logger.info(pformat(wf._steps))

