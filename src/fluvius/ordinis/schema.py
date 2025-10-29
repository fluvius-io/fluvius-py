import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg
from fluvius.data import DomainSchema, SqlaDriver, FluviusJSONField
from .status import StepStatus, TaskStatus, WorkflowStatus, StageStatus
from . import config

DB_SCHEMA = config.ORDINIS_RESOURCE_SCHEMA
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
class NavaWorkflowConnector(SqlaDriver):
    __db_dsn__ = DB_DSN
    __schema__ = DB_SCHEMA
