from fluvius.error import UnprocessableError


class StepTransitionError(UnprocessableError):
    pass


class WorkflowConfigurationError(UnprocessableError):
    pass


class WorkflowExecutionError(UnprocessableError):
    pass


class WorkflowCommandError(UnprocessableError):
    pass
