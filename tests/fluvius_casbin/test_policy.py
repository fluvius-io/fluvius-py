import re
import pytest
from fluvius.auth import AuthorizationContext, KeycloakTokenPayload, SessionProfile, SessionOrganization
from fluvius.data import SqlaDriver, DataAccessManager, UUID_TYPE
from fluvius.casbin import PolicySchema, PolicyManager, PolicyRequest, logger
from fluvius_test.helper import _csv

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
    _source = source if source else _csv(table)
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
        source=_csv("policy")
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
        user-2:
            - pro-4:
                - org-2: admin
                    - proj-2: project-admin
    """
    mapping = {
        "user-1": UUID_TYPE("123e4567-e89b-12d3-a456-426614174001"),
        "user-2": UUID_TYPE("123e4567-e89b-12d3-a456-426614174002"),
        "pro-1":  UUID_TYPE("123e4567-e89b-12d3-a456-426614174003"),
        "pro-2":  UUID_TYPE("123e4567-e89b-12d3-a456-426614174004"),
        "pro-3":  UUID_TYPE("123e4567-e89b-12d3-a456-426614174005"),
        "pro-4":  UUID_TYPE("123e4567-e89b-12d3-a456-426614174006"),
        "org-1":  UUID_TYPE("123e4567-e89b-12d3-a456-426614174007"),
        "org-2":  UUID_TYPE("123e4567-e89b-12d3-a456-426614174008"),
        "proj-1": UUID_TYPE("123e4567-e89b-12d3-a456-426614174009"),
        "proj-2": UUID_TYPE("123e4567-e89b-12d3-a456-42661417400a"),
        "proj-3": UUID_TYPE("123e4567-e89b-12d3-a456-42661417400b"),
        "proj-4": UUID_TYPE("123e4567-e89b-12d3-a456-42661417400c"),
    }
    test_cases = [
        ("user-1", "pro-1", "org-1", "", "fluvius-project:create-project", "COMMAND", True, "Allow admin to create project in org-1", {}),
        ("user-1", "pro-1", "org-1", "proj-1", "fluvius-project:update-project", "COMMAND", True, "Allow admin to update project-1 in org-1", {}),
        ("user-1", "pro-2", "org-1", "proj-1", "fluvius-project:update-project", "COMMAND", True, "Allow project-admin to update project-1 in org-1", {}),
        ("user-1", "pro-2", "org-1", "", "fluvius-project:create-project", "COMMAND", False, "Deny member to create project in org-1", {}),
        ("user-1", "pro-1", "org-2", "", "fluvius-project:create-project", "COMMAND", False, "Deny admin to create project in org-2 (wrong organization)", {}),
        
        ("user-1", "pro-1", "org-1", "", "fluvius-project.view-project", "QUERY", True, "Allow admin to view projects in org-1",{'.and': [{'.and': [{'org:eq': '123e4567-e89b-12d3-a456-426614174007'}]}]}),
        ("user-2", "pro-4", "org-2", "", "fluvius-project.view-project", "QUERY", True, "Allow admin with project-admin role to view projects in org-2",{'.and': [{'.and': [{'org:eq': '123e4567-e89b-12d3-a456-426614174008'}]}]}),
        ("user-1", "pro-3", "org-1", "", "fluvius-project.view-project", "QUERY", True, "Allow member with project-member role to view projects in org-1",{'.and': [{'.and': [{'org:eq': '123e4567-e89b-12d3-a456-426614174007'}, {'project_id:in': ['123e4567-e89b-12d3-a456-426614174009']}]}]}),
    ]

    for test_case in test_cases:
        usr, sub, org, rid, act, cqrs, allowed, message, restriction = test_case
        usr = mapping[usr]
        sub = mapping[sub]
        org = mapping[org]
        rid = str(mapping[rid] if rid else rid)
        request = PolicyRequest(
            auth_ctx=AuthorizationContext(
                user=KeycloakTokenPayload(
                    sub=usr, 
                    exp=1000,
                    iat=1000,
                    auth_time=1000,
                    jti=UUID_TYPE('123e4567-e89b-12d3-a456-426614174000'),
                    iss='https://example.com',
                    aud='example',
                    typ='ID',
                    azp='example',
                    nonce='example',
                    session_state=UUID_TYPE('123e4567-e89b-12d3-a456-426614174000'),
                    at_hash='example',
                    acr='example',
                    sid=UUID_TYPE('123e4567-e89b-12d3-a456-426614174000'),
                    email_verified=True,
                    name='example',
                    preferred_username='example',
                    given_name='example',
                    family_name='example',
                    email='example@example.com',
                    realm_access={'roles': ['admin']},
                    resource_access={'example': {'roles': ['admin']}}),
                profile=SessionProfile(id=sub,
                    name='example',
                    family_name='example',
                    given_name='example',
                    email='example@example.com',
                    username='example',
                    roles=tuple(),
                    org_id=org,
                    usr_id=usr),
                organization=SessionOrganization(id=org, name='example'),
                iamroles=tuple(),
                realm='example',
            ),
            act=act,
            rid=rid,
            cqrs=cqrs,
            msg="Test Request"
        )
        async with policy_manager._dam.transaction():
            response = await policy_manager.check_permission(request)
            assert response.allowed is allowed, message

            if cqrs == "QUERY":
                logger.info(f"Actual Restriction: {restriction}")
                logger.info(f"Policy Restriction: {response.narration.restriction}")
                assert response.narration.restriction == restriction
