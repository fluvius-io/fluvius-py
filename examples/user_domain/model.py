import sqlalchemy as sa
from fluvius.data import SqlaDataSchema, SqlaDriver, DataAccessManager


class UserConnector(SqlaDriver):
    __db_dsn__ = "sqlite+aiosqlite:////tmp/fluvius_user_domain.sqlite"


class UserSchemaBase(SqlaDataSchema):
    __abstract__ = True

    def __init_subclass__(cls):
        cls._register_with_driver(UserConnector)


class User(UserSchemaBase):
    _id = sa.Column(sa.String, primary_key=True)
    name = sa.Column(sa.String)
    _created = sa.Column(sa.DateTime(timezone=True))
    _updated = sa.Column(sa.DateTime(timezone=True))
    _deleted = sa.Column(sa.DateTime(timezone=True))
    _etag = sa.Column(sa.String)


class FluviusAccessManager(DataAccessManager):
    __connector__ = UserConnector
    __auto_model__ = True
