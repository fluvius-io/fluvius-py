import sqlalchemy as sa
from fluvius.data import SqlaDataSchema, SqlaDriver, DataAccessManager
from sqlalchemy.dialects import postgresql as pg
from fluvius.data import UUID_GENR

class UserConnector(SqlaDriver):
    __db_dsn__ = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"


class User(UserConnector.__data_schema_base__):
    __tablename__ = "user"

    _id = sa.Column(pg.UUID, primary_key=True, default=UUID_GENR)
    name = sa.Column(sa.String)
    _created = sa.Column(sa.DateTime(timezone=True))
    _updated = sa.Column(sa.DateTime(timezone=True))
    _etag = sa.Column(sa.String)
    _deleted = sa.Column(sa.DateTime(timezone=True))
    _creator = sa.Column(pg.UUID)
    _updater = sa.Column(pg.UUID)
    _realm = sa.Column(sa.String)


class FluviusAccessManager(DataAccessManager):
    __connector__ = UserConnector
    __automodel__ = True
