from fluvius.data import DataElement, field, UUIDField


class WorkflowContext(DataElement):
    user_id = UUIDField()
    source = field()
