import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg
from fluvius.data import DomainSchema, SqlaDriver, FluviusJSONField
from .status import StepStatus, TaskStatus, WorkflowStatus


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
    revision = sa.Column(sa.Integer, nullable=False)
    route_id = sa.Column(sa.UUID, nullable=False)
    title = sa.Column(sa.String, nullable=True)
    desc = sa.Column(sa.String, nullable=True)
    note = sa.Column(sa.String, nullable=True)
    status = sa.Column(sa.Enum(WorkflowStatus, name="workflow_status"), nullable=False)
    paused = sa.Column(sa.Enum(WorkflowStatus, name="workflow_status"), nullable=True)
    progress = sa.Column(sa.Float, default=0.0)
    ts_start = sa.Column(sa.DateTime(timezone=True), nullable=True)
    ts_expire = sa.Column(sa.DateTime(timezone=True), nullable=True)
    ts_finish = sa.Column(sa.DateTime(timezone=True), nullable=True)
    sys_tag = sa.Column(pg.ARRAY(sa.String), nullable=True)
    usr_tag = sa.Column(pg.ARRAY(sa.String), nullable=True)


class WorkflowStep(WorkflowBaseSchema):
    __tablename__ = "workflow-step"

    workflow_id = sa.Column(pg.UUID, sa.ForeignKey('workflow-manager.workflow._id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    workflow_stage = sa.Column(sa.String, nullable=True)
    index = sa.Column(sa.Integer, nullable=False)
    owner_id = sa.Column(pg.UUID, nullable=True)
    selector = sa.Column(pg.UUID, nullable=True)
    stm_state = sa.Column(sa.String, nullable=False)
    step_key = sa.Column(sa.String, nullable=False)
    title = sa.Column(sa.String, nullable=False)
    origin_step = sa.Column(pg.UUID, nullable=True)
    status = sa.Column(sa.Enum(StepStatus, name="step_status"), nullable=False)
    label = sa.Column(sa.String, nullable=True)
    ts_due = sa.Column(sa.DateTime(timezone=True), nullable=True)
    ts_start = sa.Column(sa.DateTime(timezone=True), nullable=True)
    ts_finish = sa.Column(sa.DateTime(timezone=True), nullable=True)
    ts_transit = sa.Column(sa.DateTime(timezone=True), nullable=True)


class WorkflowStage(WorkflowBaseSchema):
    __tablename__ = "workflow-stage"

    workflow_id = sa.Column(pg.UUID, sa.ForeignKey('workflow-manager.workflow._id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    key = sa.Column(sa.String, nullable=True)
    title = sa.Column(sa.String, nullable=True)
    desc = sa.Column(sa.String, nullable=True)
    order = sa.Column(sa.Integer, nullable=True)


class WorkflowParticipant(WorkflowBaseSchema):
    __tablename__ = "workflow-participant"

    workflow_id = sa.Column(pg.UUID, sa.ForeignKey('workflow-manager.workflow._id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    user_id = sa.Column(pg.UUID, nullable=False)
    role = sa.Column(sa.String, nullable=False)


class WorkflowMemory(WorkflowBaseSchema):
    __tablename__ = "workflow-memory"

    workflow_id = sa.Column(pg.UUID, sa.ForeignKey('workflow-manager.workflow._id', ondelete='CASCADE', onupdate='CASCADE'), unique=True, nullable=False)
    memory = sa.Column(FluviusJSONField, nullable=True)
    params = sa.Column(FluviusJSONField, nullable=True)
    stepsm = sa.Column(FluviusJSONField, nullable=True)


class WorkflowMutation(WorkflowBaseSchema):
    __tablename__ = "workflow-mutation"

    name = sa.Column(sa.String, nullable=False)
    transaction_id = sa.Column(pg.UUID, nullable=False)
    workflow_id = sa.Column(pg.UUID, sa.ForeignKey('workflow-manager.workflow._id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    action = sa.Column(sa.String, nullable=False)
    mutation = sa.Column(FluviusJSONField, nullable=False)
    step_id = sa.Column(pg.UUID, nullable=True)
    order = sa.Column(sa.Integer, nullable=False)


class WorkflowMessage(WorkflowBaseSchema):
    __tablename__ = "workflow-message"

    workflow_id = sa.Column(pg.UUID, sa.ForeignKey('workflow-manager.workflow._id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    timestamp = sa.Column(sa.DateTime(timezone=True), nullable=False)
    source = sa.Column(sa.String, nullable=False)
    content = sa.Column(sa.String, nullable=False)


class WorkflowEvent(WorkflowBaseSchema):
    __tablename__ = "workflow-event"

    workflow_id = sa.Column(pg.UUID, sa.ForeignKey('workflow-manager.workflow._id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    transaction_id = sa.Column(pg.UUID, nullable=False)
    event_name = sa.Column(sa.String, nullable=False)
    event_args = sa.Column(FluviusJSONField, nullable=True)
    event_data = sa.Column(FluviusJSONField, nullable=True)
    step_id = sa.Column(pg.UUID, nullable=True)
    order = sa.Column(sa.Integer, nullable=False)


class WorkflowTask(WorkflowBaseSchema):
    __tablename__ = "workflow-task"

    workflow_id = sa.Column(pg.UUID, sa.ForeignKey('workflow-manager.workflow._id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    step_id = sa.Column(sa.String, nullable=False)
    ts_expire = sa.Column(sa.DateTime(timezone=True), nullable=True)
    ts_start = sa.Column(sa.DateTime(timezone=True), nullable=True)
    ts_end = sa.Column(sa.DateTime(timezone=True), nullable=True)
    status = sa.Column(sa.Enum(TaskStatus, name="task_status"), nullable=False)
    name = sa.Column(sa.String, nullable=True)
    desc = sa.Column(sa.String, nullable=True)


from sqlalchemy import (
    create_engine, Column, Integer, String, ForeignKey,
    event, DDL, MetaData, select, text
)


create_view_workflow = DDL('''
CREATE OR REPLACE VIEW "workflow-manager"."_workflow" AS
SELECT
  wf.*,
  wm.stepsm,
  wm.params,
  wm.memory,
  jsonb_agg(
    jsonb_build_object(
      '_id', ws._id,
      'title', ws.title,
      'key', ws.key
    )
  ) AS stages
FROM "workflow-manager"."workflow" wf
LEFT JOIN "workflow-manager"."workflow-stage" ws ON ws.workflow_id = wf._id
LEFT JOIN "workflow-manager"."workflow-memory" wm ON wm._id = wf._id
GROUP BY wf._id, wm._id;
''')

drop_view_workflow = DDL(f"DROP VIEW IF EXISTS _workflow;")
event.listen(WorkflowBaseSchema.metadata, "before_drop", drop_view_workflow)
event.listen(WorkflowBaseSchema.metadata, "after_create", create_view_workflow)
