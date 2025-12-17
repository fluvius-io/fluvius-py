from . import config

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg
from fluvius.data import DomainSchema, SqlaDriver, FluviusJSONField

from .status import StepStatus, TaskStatus, WorkflowStatus, StageStatus
from .schema import WorkflowBaseSchema

class WorkflowViewSchema(WorkflowBaseSchema):
    __tablename__ = "_workflow"
    __external__ = True
    __table_args__ = {'info': {'is_view': True}}

    owner_id = sa.Column(pg.UUID, nullable=True)
    company_id = sa.Column(sa.String, nullable=True)
    wfdef_key = sa.Column(sa.String, nullable=False)
    wfdef_rev = sa.Column(sa.Integer, nullable=False)
    resource_id = sa.Column(sa.UUID, nullable=False)
    resource_name = sa.Column(sa.String, nullable=True)
    steps = sa.Column(pg.JSONB, nullable=True)
    title = sa.Column(sa.String, nullable=True)
    desc = sa.Column(sa.String, nullable=True)
    note = sa.Column(sa.String, nullable=True)
    status = sa.Column(sa.Enum(WorkflowStatus, name="workflow_status"), nullable=False)
    paused = sa.Column(sa.Enum(WorkflowStatus, name="workflow_status"), nullable=True)
    output = sa.Column(pg.JSONB, nullable=True)
    stages = sa.Column(pg.JSONB, nullable=True)
    stepsm = sa.Column(pg.JSONB, nullable=True)
    params = sa.Column(pg.JSONB, nullable=True)
    memory = sa.Column(pg.JSONB, nullable=True)
    progress = sa.Column(sa.Float, default=0.0)
    ts_start = sa.Column(sa.DateTime(timezone=True), nullable=True)
    ts_expire = sa.Column(sa.DateTime(timezone=True), nullable=True)
    ts_finish = sa.Column(sa.DateTime(timezone=True), nullable=True)
    sys_tag = sa.Column(pg.ARRAY(sa.String), nullable=True)
    usr_tag = sa.Column(pg.ARRAY(sa.String), nullable=True)
