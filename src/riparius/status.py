import enum

class StageStatus(enum.Enum):
    ACTIVE      = "ACTIVE"      # There are remaining unfinished steps
    ERROR       = "ERROR"       # One or more steps are in error state
    COMPLETED   = "COMPLETED"   # Everything finished


class StepStatus(enum.Enum):
    """
    If a step is in error state, it can be either aborted or skipped or recovered.
    - If it is aborted, the whole workflow will be failed.
    - If it is skipped, the workflow can be continued. The step cannot be recovered.
    - If it is recovered, the step status will be set to active. Retry count will be increased.

    TRANSITIONS:
    - Step activities: ACTIVE -> ERROR | COMPLETED | CANCELLED
    - Error recovery: ERROR -> ACTIVE
    - Error termination: ERROR -> IGNORED
        - if user don't either recover or cancel, they can abort the workflow instead.
        The workflow will be marked as failed.
    - Finished: COMPLETED | CANCELLED | FAILED | ABORTED
    """
    ACTIVE      = "ACTIVE"      # Ready to accept events
    ERROR       = "ERROR"       # Encountered an error, waiting for user confirmation
    COMPLETED   = "COMPLETED"   # Step completed successfully
    CANCELLED   = "CANCELLED"   # User cancelled workflow without any error
    IGNORED     = "IGNORED"     # User ignored the error and continue the workflow

StepStatus._FINISHED = (StepStatus.COMPLETED, StepStatus.IGNORED, StepStatus.CANCELLED)


class WorkflowStatus(enum.Enum):
    """
    TRANSITIONS:
    - Start of workflow: NEW -> ACTIVE
    - Active workflow: ACTIVE -> COMPLETED | CANCELLED | DEGRADED
    - Error workflow: DEGRADED -> ACTIVE | FAILED
    - Finished workflow: COMPLETED | CANCELLED | FAILED
    """
    NEW         = "NEW"         # no step created, workflow not yet active
    ACTIVE      = "ACTIVE"      # all step is either active or finished
    DEGRADED    = "DEGRADED"    # there is a one or more error steps

    FAILED      = "FAILED"      # there is an unrecoverable error
    COMPLETED   = "COMPLETED"   # all steps finished
    CANCELLED   = "CANCELLED"   # user cancelled workflow without any error

WorkflowStatus._FINISHED = (WorkflowStatus.COMPLETED, WorkflowStatus.CANCELLED, WorkflowStatus.FAILED)
WorkflowStatus._ACTIVE     = (WorkflowStatus.ACTIVE, WorkflowStatus.DEGRADED)
WorkflowStatus._EDITABLE   = (WorkflowStatus.ACTIVE, WorkflowStatus.DEGRADED, WorkflowStatus.NEW)
WorkflowStatus._INACTIVE   = (WorkflowStatus.CANCELLED, WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.NEW)


class TaskStatus(enum.Enum):
    """
    TRANSITIONS:
    - Start of task: SCHEDULED -> RUNNING
    - Running task: RUNNING -> FAILED | COMPLETED | CANCELLED
    - Finished task: COMPLETED | CANCELLED | FAILED
    """
    SCHEDULED   = "SCHEDULED"
    RUNNING     = "RUNNING"
    FAILED      = "FAILED"
    COMPLETED   = "COMPLETED"
    CANCELLED   = "CANCELLED"


class WorkflowDefinitionStatus(enum.Enum):
    ACTIVE      = "ACTIVE"
    INACTIVE    = "INACTIVE"
    DEPRECATED  = "DEPRECATED"




