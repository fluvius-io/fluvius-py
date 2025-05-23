import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg
from types import SimpleNamespace

from fluvius.domain import config, entity
from fluvius.domain.activity import ActivityType
from fluvius.domain.context import DomainTransport

from fluvius.data import SqlaDataSchema, SqlaDriver, UUID_GENR, DataFeedManager
from fluvius.helper import camel_to_lower

from .base import DomainLogStore

LOG_STORE_SCHEMA = config.SQL_LOG_STORE_NAMESPACE

class DomainLogConnector(SqlaDriver):
    __db_dsn__ = config.SQL_LOG_DB_DSN


class SQLDomainLogManager(DataFeedManager):
    __connector__ = DomainLogConnector
    __automodel__ = True


class SQLDomainLogStore(SQLDomainLogManager, DomainLogStore):
    def _add_entry(self, resource, data):
        return self.insert_data(resource, data.serialize())


class DomainLogBaseModel(SqlaDataSchema):
    __abstract__ = True
    __table_args__ = dict(schema=LOG_STORE_SCHEMA, extend_existing=True)

    _id = sa.Column(pg.UUID, primary_key=True, nullable=False, default=UUID_GENR, server_default=sa.text("uuid_generate_v1()"))
    _created = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    _creator = sa.Column(pg.UUID, default=UUID_GENR)

    def __init_subclass__(cls):
        DomainLogConnector.register_schema(cls)


class ContextLog(DomainLogBaseModel):
    domain = sa.Column(sa.String)
    revision = sa.Column(sa.Integer())

    realm = sa.Column(sa.String)
    dataset_id = sa.Column(pg.UUID)
    request_id = sa.Column(pg.UUID)
    user_id = sa.Column(pg.UUID)
    profile_id = sa.Column(pg.UUID)
    organization_id = sa.Column(pg.UUID)
    iam_roles = sa.Column(sa.ARRAY(sa.String))

    session = sa.Column(sa.String())
    timestamp = sa.Column(sa.DateTime(timezone=True))
    transport = sa.Column(sa.Enum(DomainTransport))
    source = sa.Column(pg.JSON())
    headers = sa.Column(pg.JSON())


class ActivityLog(DomainLogBaseModel):
    _source = sa.Column(sa.String)

    domain = sa.Column(sa.String)
    identifier = sa.Column(pg.UUID)
    resource = sa.Column(sa.String)

    message = sa.Column(sa.String())
    msgtype = sa.Column(
        sa.Enum(ActivityType, schema=LOG_STORE_SCHEMA, name="activity_msg_type")
    )
    msglabel = sa.Column(sa.String())

    context = sa.Column(pg.UUID)
    src_cmd = sa.Column(pg.UUID)
    src_evt = sa.Column(pg.UUID)
    data = sa.Column(pg.JSON)
    code = sa.Column(sa.Integer)


class EventLog(DomainLogBaseModel):
    domain = sa.Column(sa.String)
    event = sa.Column(sa.String)
    identifier = sa.Column(pg.UUID)
    resource = sa.Column(sa.String)
    src_cmd = sa.Column(pg.UUID)
    args = sa.Column(pg.JSON)
    data = sa.Column(pg.JSON)


class MessageLog(DomainLogBaseModel):
    domain = sa.Column(sa.String)
    src_cmd = sa.Column(pg.UUID)
    message = sa.Column(sa.String)
    data = sa.Column(pg.JSON)


class CommandLog(DomainLogBaseModel):
    domain = sa.Column(sa.String)
    identifier = sa.Column(pg.UUID)
    resource = sa.Column(sa.String)
    revision = sa.Column(sa.Integer())
    command = sa.Column(sa.String)
    domain_sid = sa.Column(pg.UUID)
    domain_iid = sa.Column(pg.UUID)
    payload = sa.Column(pg.JSON())

    context = sa.Column(pg.UUID, nullable=False)
    status = sa.Column(
        sa.Enum(
            entity.CommandState, schema=LOG_STORE_SCHEMA, name="command_status"
        )
    )


class IncompatibleCommandLog(DomainLogBaseModel):
    domain = sa.Column(sa.String)
    identifier = sa.Column(pg.UUID)
    resource = sa.Column(sa.String)
    revision = sa.Column(sa.Integer())
    domain_sid = sa.Column(pg.UUID)
    domain_iid = sa.Column(pg.UUID)

    selector__identifier = sa.Column(pg.UUID)
    selector__resource = sa.Column(sa.String())

    context = sa.Column(pg.UUID, nullable=False)
    status = sa.Column(
        sa.Enum(
            entity.CommandState, schema=LOG_STORE_SCHEMA, name="command_status"
        )
    )
    payload = sa.Column(pg.JSON())
    message = sa.Column(sa.String)


class PendingCommandLog(DomainLogBaseModel):
    domain = sa.Column(sa.String)
    identifier = sa.Column(pg.UUID)
    resource = sa.Column(sa.String)
    selector__identifier = sa.Column(pg.UUID)
    selector__resource = sa.Column(sa.String())

    context = sa.Column(pg.UUID, nullable=False)
    status = sa.Column(sa.Enum(entity.CommandState))
    domain = sa.Column(sa.String())
    transact = sa.Column(pg.UUID)
    data = sa.Column(pg.JSON())
    stream_id = sa.Column(pg.UUID)
    cmd_action = sa.Column(sa.Enum(entity.CommandAction))
    message = sa.Column(sa.String())

    _domain = sa.Column(sa.String)
    _kind = sa.Column(sa.Enum(entity.DomainEntityType))
    _created = sa.Column(sa.DateTime(timezone=True))
    _updated = sa.Column(sa.DateTime(timezone=True))
    _vers = sa.Column(sa.Integer())


class PendingCommandFileLog(DomainLogBaseModel):
    command_id = sa.Column(pg.UUID)
    src_file_id = sa.Column(pg.UUID)
    dst_file_id = sa.Column(pg.UUID)
    _created = sa.Column(sa.DateTime(timezone=True))


class PendingUpdateLog(DomainLogBaseModel):
    action = sa.Column(sa.String)
    note = sa.Column(sa.String)
    requester = sa.Column(pg.UUID)
    request_time = sa.Column(sa.DateTime)
    commit_time = sa.Column(sa.DateTime)
    status = sa.Column(sa.String)
    committer = sa.Column(pg.UUID)


class PendingUpdateNarrationLog(DomainLogBaseModel):
    update_id = sa.Column(pg.UUID)
    field_name = sa.Column(sa.String)
    new_value = sa.Column(sa.String)
    format = sa.Column(sa.String)
    old_value = sa.Column(sa.String)
    narration = sa.Column(pg.JSON)
