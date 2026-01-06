from . import config

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg
from fluvius.data import DomainSchema, SqlaDriver, FluviusJSONField

from .status import StepStatus, TaskStatus, WorkflowStatus, StageStatus


DB_SCHEMA = config.DB_SCHEMA
DB_DSN = config.DB_DSN

# Function to create foreign key references to workflow table
def workflow_fk(constraint_name, **kwargs):
    """Create a foreign key reference to the workflow table"""
    return sa.Column(pg.UUID, sa.ForeignKey(
        f'{DB_SCHEMA}.workflow._id',
        ondelete='CASCADE',
        onupdate='CASCADE',
        name=f'fk_workflow_{constraint_name}'
    ), nullable=False, **kwargs)


# --- Connector and Base Schema ---
class WorkflowConnector(SqlaDriver):
    __db_dsn__ = DB_DSN
    __schema__ = DB_SCHEMA


class WorkflowBaseSchema(WorkflowConnector.__data_schema_base__, DomainSchema):
    __abstract__ = True


# --- Models ---
class WorkflowSchema(WorkflowBaseSchema):
    __tablename__ = "workflow"
    __table_args__ = (
        sa.UniqueConstraint('resource_id', 'resource_name', 'wfdef_key', name='wf_resource_resource_id')
    )

    owner_id = sa.Column(pg.UUID, nullable=True)
    company_id = sa.Column(sa.String, nullable=True)
    wfdef_key = sa.Column(sa.String, nullable=False)
    wfdef_rev = sa.Column(sa.Integer, nullable=False)
    resource_id = sa.Column(sa.UUID, nullable=False)
    resource_name = sa.Column(sa.String, nullable=True)
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
    __tablename__ = "workflow_step"

    status = sa.Column(sa.Enum(StepStatus, name="step_status"), nullable=False)
    title = sa.Column(sa.String, nullable=False)
    desc = sa.Column(sa.String, nullable=True)
    index = sa.Column(sa.Integer, nullable=False)
    workflow_id = workflow_fk("step_workflow_id")
    step_key = sa.Column(sa.String, nullable=False)
    stage_key = sa.Column(sa.String, nullable=True)
    owner_id = sa.Column(pg.UUID, nullable=True)
    selector = sa.Column(pg.UUID, nullable=True)
    stm_state = sa.Column(sa.String, nullable=False)
    stm_label = sa.Column(sa.String, nullable=True)
    src_step = sa.Column(pg.UUID, nullable=True)
    memory = sa.Column(FluviusJSONField, nullable=True)
    ts_due = sa.Column(sa.DateTime(timezone=True), nullable=True)
    ts_start = sa.Column(sa.DateTime(timezone=True), nullable=True)
    ts_finish = sa.Column(sa.DateTime(timezone=True), nullable=True)
    ts_transit = sa.Column(sa.DateTime(timezone=True), nullable=True)


class WorkflowStage(WorkflowBaseSchema):
    __tablename__ = "workflow_stage"

    workflow_id = workflow_fk("stage_workflow_id")
    key = sa.Column(sa.String, nullable=True)
    stage_name = sa.Column(sa.String, nullable=True)
    stage_type = sa.Column(sa.String, nullable=True)
    desc = sa.Column(sa.String, nullable=True)
    order = sa.Column(sa.Integer, nullable=True)
    status = sa.Column(sa.Enum(StageStatus, name="stage_status"), nullable=False)


class WorkflowParticipant(WorkflowBaseSchema):
    __tablename__ = "workflow_participant"

    workflow_id = workflow_fk("participant_workflow_id")
    user_id = sa.Column(pg.UUID, nullable=False)
    role = sa.Column(sa.String, nullable=False)


class WorkflowData(WorkflowBaseSchema):
    __tablename__ = "workflow_data"

    workflow_id = workflow_fk("memory_workflow_id", unique=True)
    params = sa.Column(FluviusJSONField, nullable=True)
    memory = sa.Column(FluviusJSONField, nullable=True)
    output = sa.Column(FluviusJSONField, nullable=True)


class WorkflowMutation(WorkflowBaseSchema):
    __tablename__ = "workflow_mutation"

    workflow_id = workflow_fk("mutation_workflow_id")
    name = sa.Column(sa.String, nullable=False)
    transaction_id = sa.Column(pg.UUID, nullable=False)
    action = sa.Column(sa.String, nullable=False)
    mutation = sa.Column(FluviusJSONField, nullable=False)
    step_id = sa.Column(pg.UUID, nullable=True)
    order = sa.Column(sa.Integer, nullable=False)


class WorkflowMessage(WorkflowBaseSchema):
    __tablename__ = "workflow_message"

    workflow_id = workflow_fk("message_workflow_id")
    timestamp = sa.Column(sa.DateTime(timezone=True), nullable=False)
    source = sa.Column(sa.String, nullable=False)
    content = sa.Column(sa.String, nullable=False)


class WorkflowActivity(WorkflowBaseSchema):
    __tablename__ = "workflow_activity"

    workflow_id = workflow_fk("activity_workflow_id")
    transaction_id = sa.Column(pg.UUID, nullable=False)
    activity_name = sa.Column(sa.String, nullable=False)
    activity_args = sa.Column(FluviusJSONField, nullable=True)
    activity_data = sa.Column(FluviusJSONField, nullable=True)
    step_id = sa.Column(pg.UUID, nullable=True)
    order = sa.Column(sa.Integer, nullable=False)


class WorkflowTask(WorkflowBaseSchema):
    __tablename__ = "workflow_task"

    workflow_id = workflow_fk("task_workflow_id")
    step_id = sa.Column(sa.String, nullable=False)
    ts_expire = sa.Column(sa.DateTime(timezone=True), nullable=True)
    ts_start = sa.Column(sa.DateTime(timezone=True), nullable=True)
    ts_end = sa.Column(sa.DateTime(timezone=True), nullable=True)
    status = sa.Column(sa.Enum(TaskStatus, name="task_status"), nullable=False)
    name = sa.Column(sa.String, nullable=True)
    desc = sa.Column(sa.String, nullable=True)


class WorkflowDefinition(WorkflowBaseSchema):
    """Store workflow definition metadata extracted from Workflow classes"""
    __tablename__ = "workflow_definition"
    __table_args__ = (
        sa.UniqueConstraint('wfdef_key', 'wfdef_rev', name='uq_wfdef_key_rev'),
    )

    wfdef_key = sa.Column(sa.String, nullable=False)
    wfdef_rev = sa.Column(sa.Integer, nullable=False)
    title = sa.Column(sa.String, nullable=False)
    namespace = sa.Column(sa.String, nullable=False)
    desc = sa.Column(sa.String, nullable=True)
    stages = sa.Column(FluviusJSONField, nullable=True)
    steps = sa.Column(FluviusJSONField, nullable=True)
    roles = sa.Column(FluviusJSONField, nullable=True)
    params_schema = sa.Column(FluviusJSONField, nullable=True)
    memory_schema = sa.Column(FluviusJSONField, nullable=True)


create_view_workflow = sa.DDL(f'''
CREATE OR REPLACE VIEW "{DB_SCHEMA}"."_workflow" AS
SELECT
  wf.*,
  wm.params,
  wm.memory,
  wm.output,
  COALESCE(
    (SELECT jsonb_object_agg(st2._id::text, st2.memory)
     FROM "{DB_SCHEMA}"."workflow_step" st2
     WHERE st2.workflow_id = wf._id AND st2.memory IS NOT NULL),
    '{{}}'::jsonb
  ) AS stepsm,
  jsonb_agg(
    DISTINCT jsonb_build_object(
      '_id', ws._id,
      'key', ws.key,
      'desc', ws.desc,
      'workflow_id', ws.workflow_id,
      'stage_name', ws.stage_name,
      'stage_type', ws.stage_type,
      'order', ws.order,
      'status', ws.status
    )
  ) FILTER (WHERE ws._id IS NOT NULL) AS stages,
  COALESCE(
      jsonb_agg(
        DISTINCT jsonb_build_object(
          '_id', st._id,
          'desc', st.desc,
          'title', st.title,
          'step_key', st.step_key,
          'stage_key', st.stage_key,
          'workflow_id', st.workflow_id,
          'selector', st.selector,
          'stm_state', st.stm_state,
          'stm_label', st.stm_label,
          'status', st.status,
          'memory', st.memory
        )
      ) FILTER (WHERE st._id IS NOT NULL),
      '[]'::jsonb
   ) AS steps
FROM "{DB_SCHEMA}"."workflow" wf
LEFT JOIN "{DB_SCHEMA}"."workflow_stage" ws ON ws.workflow_id = wf._id
LEFT JOIN "{DB_SCHEMA}"."workflow_step" st ON st.workflow_id = wf._id
LEFT JOIN "{DB_SCHEMA}"."workflow_data" wm ON wm.workflow_id = wf._id
GROUP BY wf._id, wm._id;
''')

drop_view_workflow = sa.DDL(f'''DROP VIEW IF EXISTS "{DB_SCHEMA}"._workflow;''')
sa.event.listen(WorkflowBaseSchema.metadata, "before_drop", drop_view_workflow)
sa.event.listen(WorkflowBaseSchema.metadata, "after_create", create_view_workflow)
