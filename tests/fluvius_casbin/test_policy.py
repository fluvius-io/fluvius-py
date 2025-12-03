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
        columns="ptype,role,usr,pro,org,rid,scope,act,cqrs,meta,_id,_deleted",
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
                    - proj-3: project-member
                    - proj-4: project-member
            - pro-3:
                - org-1: member
                    - proj-1: project-member
                    - proj-3: project-admin
                    - proj-4: project-member
        user-2:
            - pro-4:
                - org-2: admin
                    - proj-2: project-admin
    """
    test_cases = [
        ("user-1", "pro-1", "org-1", "", "fluvius-project:create-project", "COMMAND", True, "Allow admin to create project in org-1", {}),
        ("user-1", "pro-1", "org-1", "proj-1", "fluvius-project:update-project", "COMMAND", True, "Allow admin to update project-1 in org-1", {}),
        ("user-1", "pro-2", "org-1", "proj-1", "fluvius-project:update-project", "COMMAND", True, "Allow project-admin to update project-1 in org-1", {}),
        ("user-1", "pro-1", "org-1", "user-1", "fluvius-user:update-user", "COMMAND", True, "Allow user-admin to update user-1 in org-1", {}),
        ("user-1", "pro-2", "org-1", "", "fluvius-project:create-project", "COMMAND", False, "Deny member to create project in org-1", {}),
        ("user-1", "pro-1", "org-2", "", "fluvius-project:create-project", "COMMAND", False, "Deny admin to create project in org-2 (wrong organization)", {}),
        
        ("user-1", "pro-1", "org-1", "", "fluvius-project.view-project", "QUERY", True, "Allow admin to view projects in org-1",{'.and': [{'.and': [{'org:eq': 'org-1'}]}]}),
        # ("user-1", "pro-2", "org-1", "", "fluvius-project.view-project", "QUERY", True, "Allow member with project-admin, project-member role to view projects in org-1",{'.and': [{'.and': [{'org:eq': 'org-1'}, {'project_id:in': ['proj-1', 'proj-3', 'proj-4']}]}]}),
    ]

    for test_case in test_cases:
        usr, sub, org, rid, act, cqrs, allowed, message, restriction = test_case
        request = PolicyRequest(
            usr=usr,
            pro=sub,
            org=org,
            rid=rid,
            act=act,
            cqrs=cqrs,
        )
        async with policy_manager._dam.transaction():
            response = await policy_manager.check_permission(request)
            assert response.allowed is allowed, message

            if cqrs == "QUERY":
                logger.info(f"Restriction: {response.narration.restriction}")
                logger.info(f"Restriction: {restriction}")
                assert response.narration.restriction == restriction
