from fluvius.exceptions import UnprocessableError


class StepTransitionError(UnprocessableError):
    pass


class WorkflowConfigurationError(UnprocessableError):
    pass


class WorkflowExecutionError(UnprocessableError):
    pass
