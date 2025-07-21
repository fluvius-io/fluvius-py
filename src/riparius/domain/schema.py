import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg
from fluvius.data import DomainSchema, SqlaDriver, DataAccessManager
from ..status import StepStatus, TaskStatus, WorkflowStatus


# --- Connector and Base Schema ---
class WorkflowConnector(SqlaDriver):
    __db_dsn__ = "postgresql+asyncpg://fluvius_test@localhost/fluvius_test"
    __schema__ = "workflow-manager"


class WorkflowBaseSchema(WorkflowConnector.__data_schema_base__, DomainSchema):
    __abstract__ = True


# --- Models ---
class WorkflowSchema(WorkflowBaseSchema):
    __tablename__ = "workflow"

    owner_id = sa.Column(pg.UUID, nullable=True)
    company_id = sa.Column(sa.String, nullable=True)
    revison = sa.Column(sa.Integer, nullable=False)
    route_id = sa.Column(sa.String, nullable=False)
    title = sa.Column(sa.String, nullable=True)
    desc = sa.Column(sa.String, nullable=True)
    note = sa.Column(sa.String, nullable=True)
    status = sa.Column(sa.Enum(WorkflowStatus, name="workflow_status"), nullable=False)
    progress = sa.Column(sa.Float, default=0.0)
    ts_start = sa.Column(sa.DateTime(timezone=True), nullable=True)
    ts_expire = sa.Column(sa.DateTime(timezone=True), nullable=True)
    ts_finish = sa.Column(sa.DateTime(timezone=True), nullable=True)
    ts_transit = sa.Column(sa.DateTime(timezone=True), nullable=True)
    sys_tag = sa.Column(pg.ARRAY(sa.String), nullable=True)
    usr_tag = sa.Column(pg.ARRAY(sa.String), nullable=True)


class WorkflowStep(WorkflowBaseSchema):
    __tablename__ = "workflow-step"

    workflow_id = sa.Column(pg.UUID, nullable=False)
    owner_id = sa.Column(pg.UUID, nullable=True)
    stage_id = sa.Column(pg.UUID, nullable=True)
    stm_state = sa.Column(sa.String, nullable=False)
    step_name = sa.Column(sa.String, nullable=False)
    title = sa.Column(sa.String, nullable=False)
    origin_step = sa.Column(pg.UUID, nullable=True)
    status = sa.Column(sa.Enum(StepStatus, name="step_status"), nullable=False)
    label = sa.Column(sa.String, nullable=True)
    ts_due = sa.Column(sa.DateTime(timezone=True), nullable=True)
    ts_start = sa.Column(sa.DateTime(timezone=True), nullable=True)
    ts_finish = sa.Column(sa.DateTime(timezone=True), nullable=True)


class WorkflowTrigger(WorkflowBaseSchema):
    __tablename__ = "workflow-trigger"

    workflow_id = sa.Column(pg.UUID, nullable=False)
    origin_step = sa.Column(pg.UUID, nullable=True)
    trigger_name = sa.Column(sa.String, nullable=False)
    trigger_data = sa.Column(sa.JSON, nullable=False)


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
    user_id = sa.Column(pg.UUID, nullable=False)
    role = sa.Column(sa.String, nullable=False)


class WorkflowMemory(WorkflowBaseSchema):
    __tablename__ = "workflow-memory"

    workflow_id = sa.Column(pg.UUID, nullable=False)
    step_id = sa.Column(pg.UUID, nullable=True)
    memory_key = sa.Column(sa.String, nullable=False)
    memory_value = sa.Column(sa.JSON, nullable=False)


class WorkflowEvent(WorkflowBaseSchema):
    __tablename__ = "workflow-event"

    workflow_id = sa.Column(pg.UUID, nullable=False)
    transaction_id = sa.Column(sa.String, nullable=False)
    workflow_key = sa.Column(sa.String, nullable=False)
    event_name = sa.Column(sa.String, nullable=False)
    event_data = sa.Column(sa.JSON, nullable=False)
    route_id = sa.Column(sa.String, nullable=False)
    step_id = sa.Column(sa.String, nullable=False)


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
