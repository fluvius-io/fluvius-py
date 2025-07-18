from fluvius.data import DataModel, UUID_TYPE


class WorkflowContext(DataModel):
    user_id: UUID_TYPE
    source: str
