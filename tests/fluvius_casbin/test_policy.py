import re
import pytest
from fluvius.data import SqlaDriver, DataAccessManager
from fluvius.casbin import PolicySchema, PolicyManager, PolicyRequest, logger

RX_COMMA = re.compile(r"\s*[,;\s]\s*")


class PolicyConnector(SqlaDriver):
    __db_dsn__ = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"


class PolicyData(PolicyConnector.__data_schema_base__, PolicySchema):
    __tablename__ = "casbin_rule"


class PolicyAccessManager(DataAccessManager):
    __connector__ = PolicyConnector
    __automodel__ = True


class TestPolicyManager(PolicyManager):
    __schema__ = PolicyData


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
    db = engine.connector._session_configuration._async_engine
    async with db.begin() as conn:
        raw_asyncpg_conn = (await conn.get_raw_connection()).driver_connection
        await raw_asyncpg_conn.copy_to_table(table, **opts)

@pytest.mark.asyncio
async def test_project_admin_create_without_resource_id():
    dam = PolicyAccessManager(None)
    db = dam.connector._session_configuration._async_engine
    async with db.begin() as conn:
        await conn.run_sync(PolicyConnector.__data_schema_base__.metadata.drop_all)
        await conn.run_sync(PolicyConnector.__data_schema_base__.metadata.create_all)

    await copy_table_from_csv(
        engine=dam,
        schema="public",
        table="casbin_rule",
        columns="ptype,role,usr,pro,org,dom,res,rid,act,cqrs,meta,_id,_deleted",
        source="tests/_data/policy_test.csv"
    )
    policy_manager = TestPolicyManager(dam)
    """
        user-1:
            - pro-1:
                - org-1: admin
            - pro-2:
                - org-1: member
                    - proj-1: project-admin
            - pro-3:
                - org-1: member
                    - proj-1: project-member
        user-2:
            - pro-4:
                - org-2: admin
                    - proj-2: project-admin
        user-3:
            - pro-5:
                - org-system: sys_admin
        user-4:
            - pro-6
                - org-system: sys_readonly
        user-5:
            - pro-7
                - org-system: sys_audit
    """
    test_cases = [
        ("user-1", "pro-1", "org-1", "fluvius-project", "project", "", "create", "COMMAND", True, "Allow admin to create project in org-1"),
        ("user-1", "pro-1", "org-1", "fluvius-project", "project", "", "view", "QUERY", True, "Allow admin to view projects in org-1"),
        ("user-1", "pro-1", "org-1", "fluvius-project", "project", "proj-1", "update", "COMMAND", True, "Allow admin to update project-1 in org-1"),
        ("user-1", "pro-1", "org-1", "fluvius-project", "project", "proj-2", "view", "QUERY", True, "Allow admin to view project-2 in org-1"),
        ("user-1", "pro-2", "org-1", "fluvius-project", "project", "proj-1", "update", "COMMAND", True, "Allow project-admin to update project-1 in org-1"),
        ("user-1", "pro-2", "org-1", "fluvius-project", "project", "proj-1", "view", "QUERY", True, "Allow project-admin to view project-1 in org-1 (same organization)"),
        ("user-1", "pro-3", "org-1", "fluvius-project", "project", "proj-1", "view", "QUERY", True, "Allow project-member to view project-1 in org-1 (same organization)"),
        ("user-1", "pro-1", "org-1", "fluvius-user", "user", "user-1", "update", "COMMAND", True, "Allow user-admin to update user-1 in org-1"),

        # Deny test cases
        ("user-1", "pro-2", "org-1", "fluvius-project", "project", "", "create", "COMMAND", False, "Deny member to create project in org-1"),
        ("user-1", "pro-1", "org-2", "fluvius-project", "project", "", "create", "COMMAND", False, "Deny admin to create project in org-2 (wrong organization)"),
        ("user-1", "pro-1", "org-2", "fluvius-project", "project", "", "view", "QUERY", False, "Deny admin to view projects in org-2 (wrong organization)"),
        ("user-1", "pro-1", "org-1", "fluvius-project", "project", "proj-4", "update", "COMMAND", False, "Deny admin to update project-4 in org-2 (wrong project)"),
        ("user-1", "pro-1", "org-1", "fluvius-project", "project", "proj-4", "view", "QUERY", False, "Deny admin to view project-4 in org-1 (wrong project)"),
        ("user-1", "pro-3", "org-1", "fluvius-project", "project", "proj-1", "update", "COMMAND", False, "Deny project-member to update project-1 in org-1"),
        ("user-1", "pro-1", "org-1", "fluvius-user", "user", "user-2", "update", "COMMAND", False, "Deny user-admin to update user-2 in org-1 (wrong user)"),
        ("user-1", "pro-1", "org-1", "fluvius-user", "user", "user-2", "view", "QUERY", False, "Deny user-admin to view user-2 in org-1 (wrong user)"),
    ]

    for test_case in test_cases:
        usr, sub, org, dom, res, rid, act, cqrs, allowed, message = test_case
        request = PolicyRequest(
            usr=usr,
            pro=sub,
            org=org,
            dom=dom,
            res=res,
            rid=rid,
            act=act,
            cqrs=cqrs,
        )
        async with policy_manager._dam.transaction():
            response = await policy_manager.check_permission(request)
            for trace in response.narration.trace:
                logger.info(trace["detail"])
            logger.info("Test case: %s", message)
            logger.info(
                "Test case: usr=%s, pro=%s, org=%s, dom=%s, res=%s, rid=%s, act=%s, cqrs=%s, | expected=%s | actual=%s",
                request.usr, request.pro, request.org, request.dom, request.res, request.rid, request.act, request.cqrs, allowed, response.allowed
            )
            logger.info("--------------------------------")
            assert response.allowed is allowed, message
