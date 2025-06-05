import re
import pytest
import sqlalchemy as sa
from fluvius.data import SqlaDriver, DataAccessManager
from fluvius.casbin import PolicySchema, PolicyManager, PolicyRequest, logger

RX_COMMA = re.compile(r"\s*[,;\s]\s*")


class PolicyConnector(SqlaDriver):
    __db_dsn__ = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"


class PolicyData(PolicyConnector.__data_schema_base__, PolicySchema):
    __tablename__ = "casbin_rule"
    e1 = sa.Column(sa.String)
    e2 = sa.Column(sa.String)


class PolicyAccessManager(DataAccessManager):
    __connector__ = PolicyConnector
    __automodel__ = True


class TestPolicyManager(PolicyManager):
    __table__ = "casbin_rule"
    __model__ = "tests/_conf/model_2.conf"


async def copy_table_from_csv(engine, schema, table, source=None, columns=None, **options):
    _source = source if source else f"tests/_data/{table}.csv"
    opts = dict(
        schema_name=schema,
        source=_source,
        columns=RX_COMMA.split(columns) if isinstance(columns, str) else columns,
        header=True,
        quote='"',
        format='csv'
    )

    opts.update(options)
    db = engine.connector._async_session._async_engine
    async with db.begin() as conn:
        raw_asyncpg_conn = (await conn.get_raw_connection()).driver_connection
        await raw_asyncpg_conn.copy_to_table(table, **opts)


@pytest.mark.asyncio
async def test_sql_adapter():
    dam = PolicyAccessManager(None)

    db = dam.connector._async_session._async_engine
    async with db.begin() as conn:
        await conn.run_sync(PolicyConnector.__data_schema_base__.metadata.drop_all)
        await conn.run_sync(PolicyConnector.__data_schema_base__.metadata.create_all)

    await copy_table_from_csv(
        engine=dam,
        schema="public",
        table="casbin_rule",
        columns="ptype,v0,v1,v2,v3,v4,v5,e1,e2,_id,_deleted",
        source="tests/_data/policy_2.csv"
    )

    plm = TestPolicyManager(dam)
    test_cases = [
        # (profile, org, domain, resource, resource_id, action, expected_result, description)
        ("profile-123", "org-1", "domain-1", "project", "", "create", True, "project-admin creating project (no resource_id)"),
        ("profile-123", "org-1", "domain-1", "project", "proj-1", "update", True, "project-admin updating granted project"),
        ("profile-456", "org-1", "domain-1", "project", "proj-2", "view", True, "team-lead viewing granted project"),
        ("profile-456", "org-1", "domain-1", "project", "proj-1", "update", False, "team-lead lacks update permission"),
        ("profile-456", "org-1", "domain-1", "project", "", "create", False, "team-lead not allowed to create"),
        ("profile-123", "org-1", "domain-1", "project", "proj-X", "update", False, "resource not granted via g2"),
        ("profile-123", "org-2", "domain-1", "project", "", "create", False, "wrong organization for role"),
        ("profile-999", "org-1", "domain-1", "project", "proj-1", "view", False, "unknown profile"),
        ("profile-123", "org-1", "domain-1", "project", "proj-2", "view", True, "project-admin has view via update policy"),
        ("profile-123", "org-1", "domain-2", "project", "proj-1", "update", False, "wrong domain"),
        ("profile-123", "org-1", "domain-1", "project", "proj-2", "delete", False, "no delete policy defined"),
    ]

    for i, (profile, org, domain, resource, res_id, action, expected, desc) in enumerate(test_cases, 1):
        rss = await plm.check(profile, org, domain, resource, res_id, action)
        assert rss.allowed == expected
