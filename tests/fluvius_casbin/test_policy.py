import re
import pytest
from fluvius.data import SqlaDriver, DataAccessManager
from fluvius.casbin import PolicySchema, PolicyManager, PolicyRequest, logger
from fluvius.error import ForbiddenError

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
        columns="ptype,role,sub,org,dom,res,rid,act,cqrs,meta,_id,_deleted",
        source="tests/_data/policy_test.csv"
    )
    policy_manager = TestPolicyManager(dam)
    """Project admin can create projects without resource_id."""
    request = PolicyRequest(
        usr="user-123",
        sub="profile-123",
        org="org-1",
        dom="domain-1",
        res="project",
        rid="",
        act="create",
        cqrs="COMMAND"
    )
    async with policy_manager._dam.transaction():
        response = await policy_manager.check_permission(request)
        assert response.allowed is True, "Project admin should be able to create projects"

    """Project admin can update resources granted via g2."""
    request = PolicyRequest(
        usr="user-123",
        sub="profile-123",
        org="org-1",
        dom="domain-1",
        res="project",
        rid="proj-1",
        act="update",
        cqrs="COMMAND"
    )
    async with policy_manager._dam.transaction():
        response = await policy_manager.check_permission(request)
        assert response.allowed is True, "Project admin should be able to update granted projects"

    """Project admin can view resources granted via g2."""
    request = PolicyRequest(
        usr="user-123",
        sub="profile-123",
        org="org-1",
        dom="domain-1",
        res="project",
        rid="proj-2",
        act="view",
        cqrs="QUERY"
    )
    async with policy_manager._dam.transaction():
        response = await policy_manager.check_permission(request)
        assert response.allowed is True, "Project admin should be able to view granted projects"

    """Project admin can delete resources granted via g2."""
    request = PolicyRequest(
        usr="user-123",
        sub="profile-123",
        org="org-1",
        dom="domain-1",
        res="project",
        rid="proj-1",
        act="delete",
        cqrs="COMMAND"
    )
    async with policy_manager._dam.transaction():
        response = await policy_manager.check_permission(request)
        assert response.allowed is True, "Project admin should be able to delete granted projects"

    """Project admin cannot access resources not granted via g2."""
    request = PolicyRequest(
        usr="user-123",
        sub="profile-123",
        org="org-1",
        dom="domain-1",
        res="project",
        rid="proj-X",
        act="update",
        cqrs="COMMAND"
    )
    async with policy_manager._dam.transaction():
        response = await policy_manager.check_permission(request)
        assert response.allowed is False, "Project admin should not be able to access resources not granted via g2"

    """Project admin cannot access resources in wrong organization."""
    request = PolicyRequest(
        usr="user-123",
        sub="profile-123",
        org="org-2",
        dom="domain-1",
        res="project",
        rid="",
        act="create",
        cqrs="COMMAND"
    )
    async with policy_manager._dam.transaction():
        response = await policy_manager.check_permission(request)
        assert response.allowed is False, "Project admin should not be able to access resources in wrong organization"

    """Project admin cannot access resources in wrong domain."""
    request = PolicyRequest(
        usr="user-123",
        sub="profile-123",
        org="org-1",
        dom="domain-2",
        res="project",
        rid="proj-1",
        act="update",
        cqrs="COMMAND"
    )
    async with policy_manager._dam.transaction():
        response = await policy_manager.check_permission(request)
        assert response.allowed is False, "Project admin should not be able to access resources in wrong domain"

    """Team lead can view resources granted via g2."""
    request = PolicyRequest(
        usr="user-456",
        sub="profile-456",
        org="org-1",
        dom="domain-1",
        res="project",
        rid="proj-2",
        act="view",
        cqrs="QUERY"
    )
    async with policy_manager._dam.transaction():
        response = await policy_manager.check_permission(request)
        assert response.allowed is True, "Team lead should be able to view granted projects"

    """Team lead can update resources granted via g2."""
    request = PolicyRequest(
        usr="user-456",
        sub="profile-456",
        org="org-1",
        dom="domain-1",
        res="project",
        rid="proj-2",
        act="update",
        cqrs="COMMAND"
    )
    async with policy_manager._dam.transaction():
        response = await policy_manager.check_permission(request)
        assert response.allowed is True, "Team lead should be able to update granted projects"

    """Team lead cannot access resources not granted via g2."""
    request = PolicyRequest(
        usr="user-456",
        sub="profile-456",
        org="org-1",
        dom="domain-1",
        res="project",
        rid="proj-4",
        act="update",
        cqrs="COMMAND"
    )
    async with policy_manager._dam.transaction():
        response = await policy_manager.check_permission(request)
        assert response.allowed is False, "Team lead should not be able to access resources not granted via g2"

    """Team lead cannot create projects."""
    request = PolicyRequest(
        usr="user-456",
        sub="profile-456",
        org="org-1",
        dom="domain-1",
        res="project",
        rid="",
        act="create",
        cqrs="COMMAND"
    )
    async with policy_manager._dam.transaction():
        response = await policy_manager.check_permission(request)
        assert response.allowed is False, "Team lead should not be able to create projects"

    """Team lead cannot delete projects."""
    request = PolicyRequest(
        usr="user-456",
        sub="profile-456",
        org="org-1",
        dom="domain-1",
        res="project",
        rid="proj-2",
        act="delete",
        cqrs="COMMAND"
    )
    async with policy_manager._dam.transaction():
        response = await policy_manager.check_permission(request)
        assert response.allowed is False, "Team lead should not be able to delete projects"

    """Team member can view resources granted via g2."""
    request = PolicyRequest(
        usr="user-789",
        sub="profile-789",
        org="org-1",
        dom="domain-1",
        res="project",
        rid="proj-3",
        act="view",
        cqrs="QUERY"
    )
    async with policy_manager._dam.transaction():
        response = await policy_manager.check_permission(request)
        assert response.allowed is True, "Team member should be able to view granted projects"

    """Team member cannot update projects."""
    request = PolicyRequest(
        usr="user-789",
        sub="profile-789",
        org="org-1",
        dom="domain-1",
        res="project",
        rid="proj-3",
        act="update",
        cqrs="COMMAND"
    )
    async with policy_manager._dam.transaction():
        response = await policy_manager.check_permission(request)
        assert response.allowed is False, "Team member should not be able to update projects"

    """Team member cannot create projects."""
    request = PolicyRequest(
        usr="user-789",
        sub="profile-789",
        org="org-1",
        dom="domain-1",
        res="project",
        rid="",
        act="create",
        cqrs="COMMAND"
    )
    async with policy_manager._dam.transaction():
        response = await policy_manager.check_permission(request)
        assert response.allowed is False, "Team member should not be able to create projects"

    """System admin can bypass all checks via g3."""
    request = PolicyRequest(
        usr="user-999",
        sub="profile-999",
        org="org-1",
        dom="domain-1",
        res="project",
        rid="proj-1",
        act="view",
        cqrs="QUERY"
    )
    async with policy_manager._dam.transaction():
        response = await policy_manager.check_permission(request)
        assert response.allowed is True, "System admin should bypass all checks"

    """System admin can create any resource."""
    request = PolicyRequest(
        usr="user-999",
        sub="profile-999",
        org="org-1",
        dom="domain-1",
        res="project",
        rid="",
        act="create",
        cqrs="COMMAND"
    )
    async with policy_manager._dam.transaction():
        response = await policy_manager.check_permission(request)
        assert response.allowed is True, "System admin should be able to create any resource"

    """System admin can update any resource."""
    request = PolicyRequest(
        usr="user-999",
        sub="profile-999",
        org="org-1",
        dom="domain-1",
        res="project",
        rid="proj-1",
        act="update",
        cqrs="COMMAND"
    )
    async with policy_manager._dam.transaction():
        response = await policy_manager.check_permission(request)
        assert response.allowed is True, "System admin should be able to update any resource"

    """System admin can delete any resource."""
    request = PolicyRequest(
        usr="user-999",
        sub="profile-999",
        org="org-1",
        dom="domain-1",
        res="project",
        rid="proj-1",
        act="delete",
        cqrs="COMMAND"
    )
    async with policy_manager._dam.transaction():
        response = await policy_manager.check_permission(request)
        assert response.allowed is True, "System admin should be able to delete any resource"

    """User cannot access other users' g4 resources."""
    request = PolicyRequest(
        usr="user-123",
        sub="profile-123",
        org="org-1",
        dom="domain-1",
        res="project",
        rid="proj-6",
        act="view",
        cqrs="QUERY"
    )
    async with policy_manager._dam.transaction():
        response = await policy_manager.check_permission(request)
        assert response.allowed is False, "User should not access other users' g4 resources"

    """Unknown profile should be denied."""
    request = PolicyRequest(
        usr="user-unknown",
        sub="profile-unknown",
        org="org-1",
        dom="domain-1",
        res="project",
        rid="proj-1",
        act="view",
        cqrs="QUERY"
    )
    async with policy_manager._dam.transaction():
        response = await policy_manager.check_permission(request)
        assert response.allowed is False, "Unknown profile should be denied"

    """Unknown action should be denied."""
    request = PolicyRequest(
        usr="user-123",
        sub="profile-123",
        org="org-1",
        dom="domain-1",
        res="project",
        rid="proj-1",
        act="unknown-action",
        cqrs="COMMAND"
    )
    async with policy_manager._dam.transaction():
        response = await policy_manager.check_permission(request)
        assert response.allowed is False, "Unknown action should be denied"

    """Wrong resource type should be denied."""
    request = PolicyRequest(
        usr="user-123",
        sub="profile-123",
        org="org-1",
        dom="domain-1",
        res="document",
        rid="proj-1",
        act="view",
        cqrs="QUERY"
    )
    async with policy_manager._dam.transaction():
        response = await policy_manager.check_permission(request)
        assert response.allowed is False, "Wrong resource type should be denied"

    """Empty resource_id should be allowed for create action."""
    request = PolicyRequest(
        usr="user-123",
        sub="profile-123",
        org="org-1",
        dom="domain-1",
        res="project",
        rid="",
        act="create",
        cqrs="COMMAND"
    )
    async with policy_manager._dam.transaction():
        response = await policy_manager.check_permission(request)
        assert response.allowed is True, "Empty resource_id should be allowed for create"

    """Profile in org-1 cannot access org-2 resources."""
    request = PolicyRequest(
        usr="user-123",
        sub="profile-123",
        org="org-1",
        dom="domain-1",
        res="project",
        rid="proj-4",
        act="view",
        cqrs="QUERY"
    )
    async with policy_manager._dam.transaction():
        response = await policy_manager.check_permission(request)
        assert response.allowed is False, "Profile in org-1 cannot access org-2 resources"

    """Profile in org-2 can access org-2 resources."""
    request = PolicyRequest(
        usr="user-111",
        sub="profile-111",
        org="org-2",
        dom="domain-1",
        res="project",
        rid="proj-4",
        act="view",
        cqrs="QUERY"
    )
    async with policy_manager._dam.transaction():
        response = await policy_manager.check_permission(request)
        assert response.allowed is True, "Profile in org-2 can access org-2 resources"
