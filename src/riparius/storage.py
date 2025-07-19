from fluvius.data import UUID_GENR, logger
from pprint import pformat
from .datadef import WorkflowState, WorkflowStatus


class WorkflowBackend(object):
    """
    Workflow backend interface.

    This class is responsible for storing and retrieving workflow data.
    It is used by the WorkflowManager to store and retrieve workflow data.
    It is also used by the WorkflowEngine to store and retrieve workflow data.
    
    """
    def __init__(self):
        self._changes = {}
        self._workflows = {}

    def create_workflow(self, wf_def):
        wf_id = UUID_GENR()
        workflow = WorkflowState(
            id=wf_id, 
            title=wf_def.title, 
            revision=wf_def.revision,
            status=WorkflowStatus.NEW)

        self.queue_event(wf_id, 'create_workflow', workflow=workflow)
        self._workflows[wf_id] = workflow
        return workflow

    def fetch_workflow(self, wf_id):
        return self._workflows.get(wf_id)
    
    def queue_event(self, wf_id, event_type, **kwargs):
        self._changes.setdefault(wf_id, []).append(
            (event_type, kwargs)
        )

    def load_steps(self, wf_id):
        return []

    def load_memory(self, wf_id):
        return {}

    def load_tasks(self, wf_id):
        return []

    def load_participants(self, wf_id):
        return []

    def load_events(self, wf_id):
        return []

    def commit(self, wf_id):
        return self._changes.pop(wf_id, [])

