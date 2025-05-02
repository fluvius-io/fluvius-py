import enum

class StageStatus(enum.Enum):
    ACTIVE      = "ACTIVE"      # There are remaining unfinished steps
    ERROR       = "ERROR"       # Some steps are in error state
    COMPLETED   = "COMPLETED"   # Everything finished


class StepStatus(enum.Enum):
    ACTIVE      = "ACTIVE"      # Ready to accept events, before any activities (i.e. events)
    ERROR       = "ERROR"       # Encountered an error, waiting for user confirmation
    ABORTED     = "ABORTED"     # Action started. Pending confirmation from the user action, no events accepted except the confirmation event.
    COMPLETED   = "COMPLETED"   # Encountered an error, waiting for user confirmation
    SKIPPED     = "SKIPPED"

StepStatus._FINISHED = (StepStatus.COMPLETED, StepStatus.SKIPPED, StepStatus.ABORTED)


class WorkflowStatus(enum.Enum):
    BLANK       = "BLANK"       # no step created, workflow not yet active

    ACTIVE      = "ACTIVE"      # all step is either active or finished
    ERROR       = "ERROR"       # there is an error step
    PAUSED      = "PAUSED"      # do not accept events

    FAILED      = "FAILED"      # there is an aborted step
    COMPLETED   = "COMPLETED"   # all steps finished
    CANCELLED   = "CANCELLED"   # user terminate the entire workflow manually

class TaskStatus(enum.Enum):
    SCHEDULED   = "SCHEDULED"
    RUNNING     = "RUNNING"
    FAILED      = "FAILED"
    COMPLETED   = "COMPLETED"


class WorkflowDefinitionStatus(enum.Enum):
    ACTIVE      = "ACTIVE"
    INACTIVE    = "INACTIVE"
    DEPRECATED  = "DEPRECATED"


WorkflowStatus._FINISHED   = (WorkflowStatus.CANCELLED, WorkflowStatus.COMPLETED, WorkflowStatus.FAILED)
WorkflowStatus._ACTIVE     = (WorkflowStatus.ACTIVE, WorkflowStatus.ERROR, WorkflowStatus.PAUSED)
WorkflowStatus._INACTIVE   = (WorkflowStatus.BLANK, WorkflowStatus.CANCELLED, WorkflowStatus.COMPLETED, WorkflowStatus.FAILED)


