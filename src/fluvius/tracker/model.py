from enum import Enum

from arq.jobs import Job
from dataclasses import asdict, is_dataclass

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.orm import mapped_column, relationship, Mapped

from fluvius.helper.timeutil import timestamp
from fluvius.data import SqlaDataSchema, SqlaDriver, UUID_GENR

from . import config, logger


class JobStatus(Enum):
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    SUBMITTED = "SUBMITTED"
    RECEIVED = "RECEIVED"
    CANCELED = "CANCELED"

    @property
    def label(self):
        return STATUS_LABEL[self]

STATUS_LABEL = {
    JobStatus.SUCCESS: "Finished",
    JobStatus.ERROR: "Error",
    JobStatus.SUBMITTED: "Pending",
    JobStatus.CANCELED: "Canceled",
    JobStatus.RECEIVED: "In Progress"
}

class WorkerStatus(Enum):
    STARTED = 'STARTED'
    RUNNING = 'RUNNING'
    STOPPED = 'STOPPED'



class SQLTrackerConnector(SqlaDriver):
    __db_dsn__ = config.TRACKER_DSN


class SQLTrackerDataModel(SqlaDataSchema):
    __abstract__ = True
    __table_args__ = {'schema': config.TRACKER_DATA_SCHEMA}

    _id = sa.Column(pg.UUID, primary_key=True, nullable=False, default=UUID_GENR, server_default=sa.text("uuid_generate_v1()"))
    _created = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    _creator = sa.Column(pg.UUID, default=UUID_GENR)
    _realm   = sa.Column(pg.UUID)  # User profile id, using to separate tenants
    _deleted = sa.Column(sa.DateTime(timezone=True))
    _etag = sa.Column(sa.String)

    def __init_subclass__(cls):
        SQLTrackerConnector.register_schema(cls)


class Worker(SQLTrackerDataModel):
    __tablename__ = config.ARQ_WORKER_TABLE

    pid = sa.Column(sa.Integer)
    status = sa.Column(sa.Enum(WorkerStatus))
    hostname = sa.Column(sa.String)
    queue_name = sa.Column(sa.String)
    jobs_complete = sa.Column(sa.Integer)
    jobs_failed = sa.Column(sa.Integer)
    jobs_retried = sa.Column(sa.Integer)
    jobs_queued = sa.Column(sa.Integer)
    start_time = sa.Column(sa.DateTime(timezone=True))
    heart_beat = sa.Column(sa.DateTime(timezone=True))
    stop_time = sa.Column(sa.DateTime(timezone=True))


class WorkerJob(SQLTrackerDataModel):
    __tablename__ = config.WORKER_JOB_TABLE

    # default when insert, job_status = PENDING
    worker_id   = sa.Column(sa.ForeignKey(Worker._id))  # User profile id, using to separate tenants

    job_message = sa.Column(sa.String)
    job_progress = sa.Column(sa.Float)
    job_status = sa.Column(sa.Enum(JobStatus))
    job_try = sa.Column(sa.Integer)

    score = sa.Column(sa.BigInteger)

    queue_name = sa.Column(sa.String)
    function = sa.Column(sa.String)
    args = mapped_column(sa.JSON().with_variant(pg.JSONB(), "postgresql"))
    kwargs = mapped_column(sa.JSON().with_variant(pg.JSONB(), "postgresql"))
    result = mapped_column(sa.JSON().with_variant(pg.JSONB(), "postgresql"))
    err_message = sa.Column(sa.String)
    err_trace = sa.Column(sa.String)

    enqueue_time = sa.Column(sa.DateTime(timezone=True))
    start_time = sa.Column(sa.DateTime(timezone=True))
    finish_time = sa.Column(sa.DateTime(timezone=True))
    defer_time = sa.Column(sa.DateTime(timezone=True))


class JobRelation(SQLTrackerDataModel):
    __tablename__ = config.JOB_RELATION_TABLE

    job_id = sa.Column(pg.UUID)
    resource = sa.Column(sa.String)
    resource_id = sa.Column(pg.UUID)
    domain = sa.Column(sa.String)
