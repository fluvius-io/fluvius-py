import pytest
from pprint import pformat
from types import SimpleNamespace
from fluvius.navis import logger, config
from fluvius.navis import Workflow, Stage, Step, Role, connect, transition, FINISH_STATE, WorkflowEventRouter, WorkflowManager
from fluvius.data import UUID_GENF, UUID_GENR

selector01 = UUID_GENF('ST01')
resource01 = UUID_GENF('WF01')


logger.info(f'FIXTURE: selector01 = {selector01} | resource01 = {resource01}')

@pytest.fixture(scope="session")
async def workflows():
    workflows = SimpleNamespace()
    return workflows


@pytest.mark.asyncio(loop_scope="session")
async def test_workflow_01(workflows):
    manager = WorkflowManager()
    async with manager._datamgr.transaction():
        wf = manager.create_workflow('sample-process', 'test-resource', resource01, {
            'test-param': 'test-value',
            'step-selector': str(selector01)
        })
        with wf.transaction():
            wf.start()
        await manager.commit()

        evt_data = SimpleNamespace(
            resource_name='test-resource',
            resource_id=resource01,
            step_selector=selector01
        )

        workflows.id01 = wf.id

        index = 0
        async for wf in manager.process_event('test-event', evt_data):
            await manager.commit_workflow(wf)
            if index == 0:
                assert len(wf.step_id_map) == 1  # 1 steps created

            if index == 1:
                assert len(wf.step_id_map) == 3  # 3 steps created

            index += 1


@pytest.mark.asyncio(loop_scope="session")
async def test_workflow_02(workflows):
    manager = WorkflowManager()
    async with manager._datamgr.transaction():
        wf = await manager.load_workflow_by_id('sample-process', workflows.id01)

        evt_data = SimpleNamespace(
            resource_name='test-resource',
            resource_id=resource01,
            step_selector=selector01
        )

        logger.info(f'evt_data = {evt_data.__dict__}')

        index = 0
        async for wf in manager.process_event('test-event', evt_data):
            await manager.commit_workflow(wf)

            if index == 0:
                assert len(wf.step_id_map) == 3  # 3 steps from first tests

            if index == 1:
                assert len(wf.step_id_map) == 5  # 2 added by reprocessing event at step 2 steps created

            index += 1

