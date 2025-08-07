import pytest
from pprint import pformat
from types import SimpleNamespace
from riparius import logger, config
from riparius import Workflow, Stage, Step, Role, st_connect, wf_connect, transition, FINISH_STATE, ActivityRouter, WorkflowManager
from fluvius.data import UUID_GENF, UUID_GENR

selector01 = UUID_GENF('S101')
resource01 = UUID_GENR()

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
        async for wf in manager.process_event('test-event', evt_data):
            assert len(wf.step_id_map) == 3  # 3 steps created
            await manager.commit_workflow(wf)


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

        async for wf in manager.process_event('test-event', evt_data):
            assert len(wf.step_id_map) == 5  # 2 more steps created
            await manager.commit_workflow(wf)


