import re
from enum import Enum
from fluvius.data import logger, config

from fluvius.data import PClass, field
from fluvius.data import UUID_GENF, UUID_GENR, nullable, UUID_TYPE
from fluvius.helper.registry import ClassRegistry
from fluvius.helper import camel_to_lower

from .router import EventRouter, st_connect, wf_connect
from .status import *


RX_STATE = re.compile(r'^[A-Z][A-Z\d]*$')


class WorkflowState(PClass):
    _id = field(UUID_TYPE, initial=UUID_GENR)
    route_id = field(UUID_TYPE, initial=UUID_GENR)
    state = field(str)
    label = field(str)
    steps = field(list, initial=[])
    tasks = field(list, initial=[])
    roles = field(list, initial=[])
    events = field(list, initial=[])
    stages = field(list, initial=[])
    params = field(dict, initial={})
    memory = field(dict, initial={})
    status = field(WorkflowStatus, initial=lambda: WorkflowStatus.BLANK)
    strans = field(list, initial=[])  # Status transitions logs
    participants = field(list, initial=[])


class WorkflowEvent(PClass):
    workflow_id = field(mandatory=True)
    step_id = field(nullable(str), initial=None)
    event_name = field(str)
    event_data = field()


class WorkflowTask(PClass):
    pass


class WorkflowEvent(PClass):
    pass


class WorkflowRoles(PClass):
    pass


def validate_label(value):
    if not RX_STATE.match(value):
        raise ValueError(f'Invalid step state: {value}')

    return value


def validate_labels(*values):
    for v in values:
        validate_label(v)

    return values


class WorkflowStep(PClass):
    _id = field(UUID_TYPE, initial=UUID_GENR)
    selector = field(UUID_TYPE)
    workflow_id = field(UUID_TYPE)
    src_step_id = field(nullable(UUID_TYPE), initial=lambda: None)
    title = field(str)
    display = field(str)
    label = field(str, factory=validate_label)
    stage = field(str)
    status = field(StepStatus, factory=StepStatus)
    message = field(str)

WorkflowStep.EDITABLE_FIELDS = ('title', 'label', 'state', 'status', 'message', 'display')


class WorkflowStage(PClass):
    _id = field(str)
    name = field(str)
    desc = field(str)


class WorkflowParticipant(PClass):
    pass


class WorkflowParameter(PClass):
    pass


class WorkflowParameterValueType(Enum):
    UUID        = "UUID"
    STRING      = "STRING"
    INTEGER     = "INTEGER"
    DATETIME    = "DATETIME"
    ARRAY       = "ARRAY"
