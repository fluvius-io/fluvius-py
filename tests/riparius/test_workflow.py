from pprint import pformat
from types import SimpleNamespace
from riparius import logger, config
from riparius.workflow import Workflow, Stage, Step, Role, st_connect, wf_connect, transition, FINISH_STATE
from riparius.router import EventRouter
from riparius.manager import WorkflowManager
from fluvius.data import UUID_GENF


st01 = UUID_GENF('100')
wf01 = UUID_GENF('101')


class SampleProcess(Workflow, title='Sample Process', revision=1):
    ''' Sample workflow description ... '''

    Stage01 = Stage(title='Stage 01')
    Role01 = Role(title="Role 01")

    def on_start(wf_state):
        step3 = wf_state.add_step('Step03', selector=st01)
        step3.transit('MOON')

    class Step01(Step, title='Step 03', stage=Stage01):
        pass

    class Step02(Step, title="step-02a", stage=Stage01):
        pass

    class Step02b(Step, stage=Stage01):
        __title__ = "Step2B"


    class Step03(Step, title="Step 03", stage=Stage01):
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
            yield f"{state.recall()}"

        @transition('TAKE')
        def to_TAKE(state, cur_state):
            logger.info('TRANSITIONING TO TAKE: %s => %s', state._id, cur_state)

    @wf_connect('test-event')
    def test_event(workflow, trigger_data):
        workflow.memorize(test_key="workflow value 2")
        yield f"test_event ACTION! #1: {trigger_data}"
        yield f"{workflow.recall()}"


def test_workflow():
    logger.info(EventRouter.ROUTING_TABLE)
    manager = WorkflowManager()
    evt_data = SimpleNamespace(workflow_id=wf01, step_id=st01)
    wf = manager.process_activity('test-event', evt_data)[0]
    assert len(wf._steps) == 3
    logger.info(pformat(wf._steps))
    logger.info("\n" + pformat(wf.commit()))

