import pytest
from pyrsistent import pmap
from fluvius.data import UUID_GENF
from fluvius.process import (
    WorkflowRegistry, WorkflowStage, WorkflowStep,
    Workflow, listen, logger, EventRouter,
    WorkflowEngine
)


@EventRouter.router('simple')
def simple_router(evt):
    return evt.workflow_id, evt.step_id


@EventRouter.router('workflow-direct')
def workflow_direct_router(evt):
    return evt.workflow_id, None


@EventRouter.transformer('no_transform')
def simple_transformer(evt_data):
    return evt_data


@WorkflowRegistry.register
class SampleWorkflow(Workflow):
    ''' Sample workflow description ... '''
    __title__ = "Sample Workflow"
    __revision__ = 1

    class Stage01(WorkflowStage, name='stage-01'):
        __title__ = "Stage 01: Title"
        __order__ = 10

        class Step01(WorkflowStep, name='step-01'):
            pass

    stage02 = WorkflowStage('stage-02', title="Stage 02: Title")
    stage03 = WorkflowStage('stage-03', title="Stage 03: Title")

    class Step02(WorkflowStep, name="step-02a", stage="stage-02"):
        pass

    class Step02b(WorkflowStep, name="step-02b", stage="stage-02"):
        pass

    @listen('test-event', router='workflow-direct')
    def test_event(self, state, evt_name, evt_data):
        state.memorize(test_key="workflow value 2")
        yield logger.info("ACTION! #1")

    class Step03(WorkflowStep, name='step-03', stage='stage-03'):
        @listen('test-event', lambda evt: (evt.workflow_id, evt.step_id))
        def test_event(self, state, evt_name, evt_data):
            state.memorize(test_key="value")
            s1 = state.create_step('step-02b', test_key_02="value")
            s2 = state.create_step('step-02a', test_key_02=str(s1._id))
            assert s1.data.src_step == s2.data.src_step and s1.data.src_step == self._id
            yield logger.info("ACTION! #2")


@pytest.mark.asyncio
async def test_process_registration(wfdal):
    context = pmap({'user_id': UUID_GENF('test-user')})
    wfengine = WorkflowEngine.create(context, 'sample-workflow')
    first_step = wfengine.create_step('step-03', test_key_02="value")
    await wfengine.commit()

    wfengine = await EventRouter.route_event(
        context, 'test-event', pmap({
            "workflow_id": wfengine.workflow._id,
            "step_id": first_step._id
        })
    )

    await wfengine.commit()
    assert len(EventRouter.EVENT_REGISTRY) == 1
    assert len(EventRouter.EVENT_REGISTRY['test-event']) == 2
