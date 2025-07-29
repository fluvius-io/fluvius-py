import pytest
from pprint import pformat
from types import SimpleNamespace
from riparius import logger, config
from riparius import Workflow, Stage, Step, Role, st_connect, wf_connect, transition, FINISH_STATE, ActivityRouter, WorkflowManager
from fluvius.data import UUID_GENF

st01 = UUID_GENF('100')
wf01 = UUID_GENF('101') 


@pytest.mark.asyncio(loop_scope="session")
async def test_workflow():
    manager = WorkflowManager()
    evt_data = SimpleNamespace(workflow_id=wf01, step_id=st01)
    for wf in manager.process_event('test-event', evt_data):
        assert len(wf.step_id_map) == 3  # 3 steps created
        await manager.commit_workflow(wf)


