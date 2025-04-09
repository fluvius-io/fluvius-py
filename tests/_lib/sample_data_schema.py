import pytest

from enum import Enum
import asyncpg

from fluvius.base.exceptions import UnprocessableError
from fluvius.helper import camel_to_lower
from fluvius.data.data_driver import SqlaDriver
from fluvius.data.data_manager import DataAccessManager
from fluvius.data.data_schema.sqlalchemy import SqlaDataSchema, sa
from fluvius.data import logger
from sqlalchemy.dialects.postgresql import UUID

'''
CREATE USER fluvius_test WITH PASSWORD 'iyHu5WBQxiVXyLLJaYO0XJec';
CREATE DATABASE fluvius_test;
GRANT ALL PRIVILEGES ON DATABASE fluvius_test TO  fluvius_test;
'''

class SQLiteConnector(SqlaDriver):
    __db_dsn__ = "sqlite+aiosqlite:////tmp/fluvius.data.sqlite"


class SampleSchemaModelBase(SqlaDataSchema):
    __abstract__ = True

    def __init_subclass__(cls):
        cls._register_with_driver(SQLiteConnector)


class CompanyStatus(Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SETUP = "SETUP"
    REVIEW = "REVIEW"

class CompanyType(Enum):
    SYSTEM = "SYSTEM"
    NETWORK = "NETWORK"
    ORGANIZATION = "ORGANIZATION"
    CONTRACTOR = "CONTRACTOR"
    OTHER = "OTHER"
    FAMILY = "FAMILY"
    TESTING = "TESTING"
    PRODUCTION = "PRODUCTION"


class CompanySchema(SampleSchemaModelBase):
    __tablename__ = 'company'
    __etag_fields__ = (
        "_id",
        "name",
        "company_code"
    )

    _id = sa.Column(sa.String, primary_key=True)
    system_entity = sa.Column(sa.Boolean)

    business_name = sa.Column(sa.String)
    name = sa.Column(sa.String)
    tax_id = sa.Column(sa.String)
    group_npi = sa.Column(sa.String)
    description = sa.Column(sa.String)
    company_code = sa.Column(sa.String)

    active = sa.Column(sa.Boolean)
    owner_id = sa.Column(sa.String)
    default_signer_id = sa.Column(sa.String)
    verified_tax_id = sa.Column(sa.String)
    verified_npi = sa.Column(sa.String)
    user_tag = sa.Column(sa.String)
    system_tag = sa.Column(sa.String)
    status = sa.Column(sa.Enum(CompanyStatus))
    kind = sa.Column(sa.Enum(CompanyType))
    invitation_code = sa.Column(sa.String)


class CompanyMemberSchema(SampleSchemaModelBase):
    _id = sa.Column(sa.String, primary_key=True)
    member_id = sa.Column(sa.String)
    company_id = sa.Column(sa.String)
    role_id = sa.Column(UUID)
    role_key = sa.Column(sa.String)

class CompanySystemRoleSchema(SampleSchemaModelBase):

    _id = sa.Column(sa.String, primary_key=True)
    key = sa.Column(sa.String)
    role_type = sa.Column(sa.String)
    name = sa.Column(sa.String)
    official_role = sa.Column(sa.Boolean)
    default_role = sa.Column(sa.Boolean)



