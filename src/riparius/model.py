import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg
from fluvius.data import DomainSchema, SqlaDriver
from .status import StepStatus, TaskStatus, WorkflowStatus


# --- Connector and Base Schema ---
class WorkflowConnector(SqlaDriver):
    __db_dsn__ = "postgresql://user:password@localhost:5432/fluvius_workflow"


class WorkflowBaseSchema(WorkflowConnector.__data_schema_base__, DomainSchema):
    __abstract__ = True
    __table_args__ = {'schema': 'riparius'}


# --- Models ---
class WorkflowInstance(WorkflowBaseSchema):
    __tablename__ = "workflow-instance"

    owner_id = sa.Column(pg.UUID, nullable=True)
    company_id = sa.Column(sa.String, nullable=True)
    revison = sa.Column(sa.Integer, nullable=False)
    identifier = sa.Column(sa.String, nullable=False)
    title = sa.Column(sa.String, nullable=True)
    note = sa.Column(sa.String, nullable=True)
    status = sa.Column(sa.Enum(WorkflowStatus, name="workflow_status"), nullable=False)
    progress = sa.Column(sa.Float, default=0.0)
    desc = sa.Column(sa.String, nullable=True)
    started = sa.Column(sa.Boolean, nullable=True)
    ts_start = sa.Column(sa.DateTime(timezone=True), nullable=True)
    ts_due = sa.Column(sa.DateTime(timezone=True), nullable=True)
    ts_end = sa.Column(sa.DateTime(timezone=True), nullable=True)
    sys_tag = sa.Column(pg.ARRAY(sa.String), nullable=True)
    usr_tag = sa.Column(pg.ARRAY(sa.String), nullable=True)

class WorkflowStep(WorkflowBaseSchema):
    __tablename__ = "workflow-step"

    step_name = sa.Column(sa.String, nullable=False)
    title = sa.Column(sa.String, nullable=False)
    workflow_id = sa.Column(pg.UUID, nullable=False)
    stage_id = sa.Column(pg.UUID, nullable=True)
    src_step = sa.Column(pg.UUID, nullable=True)
    sys_status = sa.Column(sa.Enum(StepStatus, name="step_status"), nullable=False)
    usr_status = sa.Column(sa.String, nullable=True)
    ts_expire = sa.Column(sa.DateTime(timezone=True), nullable=True)
    ts_start = sa.Column(sa.DateTime(timezone=True), nullable=True)
    ts_end = sa.Column(sa.DateTime(timezone=True), nullable=True)

class WorkflowStage(WorkflowBaseSchema):
    __tablename__ = "workflow-stage"

    workflow_id = sa.Column(pg.UUID, nullable=False)
    key = sa.Column(sa.String, nullable=True)
    title = sa.Column(sa.String, nullable=True)
    desc = sa.Column(sa.String, nullable=True)
    order = sa.Column(sa.Integer, nullable=True)

class WorkflowParticipant(WorkflowBaseSchema):
    __tablename__ = "workflow-participant"

    workflow_id = sa.Column(pg.UUID, nullable=False)
    participant_id = sa.Column(pg.UUID, nullable=False)
    role = sa.Column(sa.String, nullable=False)

class WorkflowEvent(WorkflowBaseSchema):
    __tablename__ = "workflow-event"

    workflow_id = sa.Column(pg.UUID, nullable=False)
    participant_id = sa.Column(pg.UUID, nullable=False)
    role = sa.Column(sa.String, nullable=False)

class WorkflowTask(WorkflowBaseSchema):
    __tablename__ = "workflow-task"

    workflow_id = sa.Column(pg.UUID, nullable=False)
    step_id = sa.Column(sa.String, nullable=False)
    ts_expire = sa.Column(sa.DateTime(timezone=True), nullable=True)
    ts_start = sa.Column(sa.DateTime(timezone=True), nullable=True)
    ts_end = sa.Column(sa.DateTime(timezone=True), nullable=True)
    status = sa.Column(sa.Enum(TaskStatus, name="task_status"), nullable=False)
    name = sa.Column(sa.String, nullable=True)
    desc = sa.Column(sa.String, nullable=True)
