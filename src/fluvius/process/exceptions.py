from fluvius.base.exceptions import UnprocessableError


class StepTransitionError(UnprocessableError):
    pass


class WorkflowConfigurationError(UnprocessableError):
    pass


class WorkflowExecutionError(UnprocessableError):
    pass
