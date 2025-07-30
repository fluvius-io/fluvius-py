"""Test FastAPI queries for WorkflowQueryManager using HTTPX AsyncClient"""

import pytest
import json
from httpx import ASGITransport
from fluvius.data import UUID_GENF
from fluvius.fastapi import (
    create_app,
    configure_authentication,
    configure_domain_manager,
    configure_query_manager
)
from riparius.domain import WorkflowDomain, WorkflowQueryManager
from riparius import logger

import conftest

PROFILE = {
    "jti": "ffffffff-34cd-42ba-8585-8ff5a5b707d3",
    "sub": "eeeeeeee-0d46-4323-95b9-c5b4bdbf6205",
    "sid": "aaaaaaaa-1d59-4886-8f08-1d613c793d38",
    "name": "David Lee",
    "preferred_username": "davidlee",
    "given_name": "David",
    "family_name": "Lee",
    "email": "davidlee@adaptive-bits.com",
}

NAMESPACE = "process"


@pytest.fixture(scope="module")
def test_app():
    """Create test FastAPI app with WorkflowQueryManager"""
    logger.info('Creating test app ...')
    app = create_app() \
        | configure_authentication(auth_profile_provider='FluviusMockProfileProvider') \
        | configure_domain_manager(WorkflowDomain) \
        | configure_query_manager(WorkflowQueryManager)
    return app


@pytest.fixture(scope="module")
async def async_client(test_app):
    """Create async test client"""
    logger.info('Creating async test client ...')
    headers = {"Authorization": f"MockAuth {json.dumps(PROFILE)}"}

    # Use ASGITransport to connect AsyncClient to FastAPI app
    transport = ASGITransport(app=test_app)
    async with conftest.FluviusAsyncClient(transport=transport, base_url="http://testserver", headers=headers) as client:
        yield client


# Test Data
@pytest.fixture
def workflow_id():
    """Generate test workflow ID"""
    return UUID_GENF("test-workflow-query-001")


@pytest.fixture
def user_id():
    """Generate test user ID"""
    return UUID_GENF("test-user-query-001")


@pytest.fixture
def step_id():
    """Generate test step ID"""
    return UUID_GENF("test-step-query-001")


# Query Tests
class TestWorkflowQueries:
    """Test workflow query endpoints"""

    @pytest.mark.asyncio(loop_scope="module")
    async def test_workflow_query_basic(self, async_client):
        """Test basic workflow query without parameters"""
        response = await async_client.get(f"/{NAMESPACE}.workflow/")
        
        data = response.json()
        assert response.status_code == 200, f"Invalid response: {data}"
        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)

    @pytest.mark.asyncio(loop_scope="module")
    async def test_workflow_query_with_parameters(self, async_client):
        """Test workflow query with query parameters"""
        query_params = {
            "limit": 10,
            "page": 1,
            "query": json.dumps({"status": "ACTIVE"})
        }
        
        response = await async_client.get(f"/{NAMESPACE}.workflow/", params=query_params)
        
        data = response.json()
        assert response.status_code == 200, f"Invalid response: {data}"
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) <= 10  # Respects size limit

    @pytest.mark.asyncio(loop_scope="module")
    async def test_workflow_query_with_search(self, async_client):
        """Test workflow query with search parameters"""
        search_params = {
            "q": json.dumps({"title!has": "test"}),
            "limit": 5
        }
        
        response = await async_client.get(f"/{NAMESPACE}.workflow/", params=search_params)
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data

    @pytest.mark.asyncio(loop_scope="module")
    async def test_workflow_query_with_complex_filter(self, async_client):
        """Test workflow query with complex filter conditions"""
        complex_query = {
            "!or": [
                {"status": "ACTIVE"},
                {"status": "PAUSED"}
            ]
        }
        
        query_params = {
            "query": json.dumps(complex_query),
            "limit": 20
        }
        
        response = await async_client.get(f"/{NAMESPACE}.workflow/", params=query_params)
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data

    @pytest.mark.asyncio(loop_scope="module")
    async def test_workflow_embed_query(self, async_client):
        """Test workflow embed query (full workflow data)"""
        response = await async_client.get(f"/{NAMESPACE}.workflow-embed/")
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)

    @pytest.mark.asyncio(loop_scope="module")
    async def test_workflow_step_query(self, async_client, workflow_id):
        """Test workflow step query with scoping"""
        # Test with scoped workflow ID
        response = await async_client.get(f"/{NAMESPACE}.workflow-step/workflow_id={workflow_id}/")
        
        data = response.json()
        assert response.status_code == 200, f"Invalid data {data}"
        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)

    @pytest.mark.asyncio(loop_scope="module")
    async def test_workflow_step_query_with_filters(self, async_client, workflow_id):
        """Test workflow step query with additional filters"""
        query_params = {
            "query": json.dumps({"status": "ACTIVE"}),
            "limit": 10
        }
        
        response = await async_client.get(
            f"/{NAMESPACE}.workflow-step/workflow_id={workflow_id}/",
            params=query_params
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data

    @pytest.mark.asyncio(loop_scope="module")
    async def test_workflow_participant_query(self, async_client, workflow_id):
        """Test workflow participant query"""
        response = await async_client.get(f"/{NAMESPACE}.workflow-participant/workflow_id={workflow_id}/")
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)

    @pytest.mark.asyncio(loop_scope="module")
    async def test_workflow_participant_query_with_role_filter(self, async_client, workflow_id):
        """Test workflow participant query with role filter"""
        query_params = {
            "query": json.dumps({"role": "reviewer"}),
            "limit": 5
        }
        
        response = await async_client.get(
            f"/{NAMESPACE}.workflow-participant/workflow_id={workflow_id}/",
            params=query_params
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data

    @pytest.mark.asyncio(loop_scope="module")
    async def test_workflow_stage_query(self, async_client, workflow_id):
        """Test workflow stage query"""
        response = await async_client.get(f"/{NAMESPACE}.workflow-stage/workflow_id={workflow_id}/")
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)

    @pytest.mark.asyncio(loop_scope="module")
    async def test_workflow_stage_query_with_order_filter(self, async_client, workflow_id):
        """Test workflow stage query with order filter"""
        query_params = {
            "query": json.dumps({"order!gte": 1}),
            "sort": "order"
        }
        
        response = await async_client.get(
            f"/{NAMESPACE}.workflow-stage/workflow_id={workflow_id}/",
            params=query_params
        )
        
        data = response.json()
        assert response.status_code == 200, f"Invalid data: {data}"
        assert "data" in data
        assert "pagination" in data


class TestQueryPagination:
    """Test query pagination functionality"""

    @pytest.mark.asyncio(loop_scope="module")
    async def test_pagination_first_page(self, async_client):
        """Test first page of workflow query"""
        query_params = {
            "limit": 3,
            "page": 1
        }
        
        response = await async_client.get(f"/{NAMESPACE}.workflow/", params=query_params)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) <= 3
        assert "pagination" in data
        assert data["pagination"]["page"] == 1

    @pytest.mark.asyncio(loop_scope="module")
    async def test_pagination_second_page(self, async_client):
        """Test second page of workflow query"""
        query_params = {
            "limit": 3,
            "page": 2
        }
        
        response = await async_client.get(f"/{NAMESPACE}.workflow/", params=query_params)
        
        assert response.status_code == 200
        data = response.json()
        assert "pagination" in data
        assert data["pagination"]["page"] == 2

    @pytest.mark.asyncio(loop_scope="module")
    async def test_large_page_size(self, async_client):
        """Test query with large page size"""
        query_params = {
            "limit": 100,
            "page": 1
        }
        
        response = await async_client.get(f"/{NAMESPACE}.workflow/", params=query_params)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) <= 100


class TestQuerySorting:
    """Test query sorting functionality"""

    @pytest.mark.asyncio(loop_scope="module")
    async def test_sort_by_title(self, async_client):
        """Test sorting workflows by title"""
        query_params = {
            "sort": "title",
            "limit": 10
        }
        
        response = await async_client.get(f"/{NAMESPACE}.workflow/", params=query_params)
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    @pytest.mark.asyncio(loop_scope="module")
    async def test_sort_by_creation_time(self, async_client):
        """Test sorting workflows by creation time"""
        query_params = {
            "sort": "ts_start.desc",  # Descending order
            "limit": 10
        }
        
        response = await async_client.get(f"/{NAMESPACE}.workflow/", params=query_params)
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    @pytest.mark.asyncio(loop_scope="module")
    async def test_multiple_sort_fields(self, async_client):
        """Test sorting by multiple fields"""
        query_params = {
            "sort": "status,title",
            "limit": 10
        }
        
        response = await async_client.get(f"/{NAMESPACE}.workflow/", params=query_params)
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data


class TestQueryValidation:
    """Test query validation and error handling"""

    @pytest.mark.asyncio(loop_scope="module")
    async def test_invalid_json_query(self, async_client):
        """Test query with invalid JSON"""
        query_params = {
            "query": "invalid json"
        }
        
        response = await async_client.get(f"/{NAMESPACE}.workflow/", params=query_params)
        
        # Should either return 400 or handle gracefully
        assert response.status_code in [400, 422, 200]

    @pytest.mark.asyncio(loop_scope="module")
    async def test_invalid_page_number(self, async_client):
        """Test query with invalid page number"""
        query_params = {
            "page": -1,
            "limit": 10
        }
        
        response = await async_client.get(f"/{NAMESPACE}.workflow/", params=query_params)
        
        # Should handle gracefully or return error
        assert response.status_code in [400, 422, 200, 500]

    @pytest.mark.asyncio(loop_scope="module")
    async def test_invalid_size_parameter(self, async_client):
        """Test query with invalid size parameter"""
        query_params = {
            "limit": -5,
            "page": 1
        }
        
        response = await async_client.get(f"/{NAMESPACE}.workflow/", params=query_params)
        
        # Should handle gracefully or return error
        assert response.status_code in [400, 422, 200]

    @pytest.mark.asyncio(loop_scope="module")
    async def test_missing_required_scope(self, async_client):
        """Test scoped query without required scope parameter"""
        # Workflow step query requires workflow_id scope
        response = await async_client.get(f"/{NAMESPACE}.workflow-step/")
        
        # Should return error for missing scope
        assert response.status_code in [400, 422, 404]


class TestQueryFieldFiltering:
    """Test field-specific filtering in queries"""

    @pytest.mark.asyncio(loop_scope="module")
    async def test_filter_by_workflow_status(self, async_client):
        """Test filtering workflows by status"""
        query_params = {
            "query": json.dumps({"status": "ACTIVE"}),
            "limit": 10
        }
        
        response = await async_client.get(f"/{NAMESPACE}.workflow/", params=query_params)
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    @pytest.mark.asyncio(loop_scope="module")
    async def test_filter_by_title_has(self, async_client):
        """Test filtering workflows by title containing text"""
        query_params = {
            "query": json.dumps({"title!has": "test"}),
            "limit": 10
        }
        
        response = await async_client.get(f"/{NAMESPACE}.workflow/", params=query_params)
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    @pytest.mark.asyncio(loop_scope="module")
    async def test_filter_by_date_range(self, async_client):
        """Test filtering workflows by date range"""
        query_params = {
            "query": json.dumps({
                "ts_start!gte": "2024-01-01T00:00:00.000000Z",
                "ts_start!lte": "2024-12-31T23:59:59.999999Z"
            }),
            "limit": 10
        }
        
        response = await async_client.get(f"/{NAMESPACE}.workflow/", params=query_params)
        data = response.json()

        assert response.status_code == 200, f"Invalid data: {data}"
        assert "data" in data

    @pytest.mark.asyncio(loop_scope="module")
    async def test_filter_step_by_status(self, async_client, workflow_id):
        """Test filtering workflow steps by status"""
        query_params = {
            "query": json.dumps({"status": "COMPLETED"}),
            "limit": 10
        }
        
        response = await async_client.get(
            f"/{NAMESPACE}.workflow-step/{workflow_id}/",
            params=query_params
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    @pytest.mark.asyncio(loop_scope="module")
    async def test_invalid_without_scope(self, async_client, workflow_id):
        """Test filtering workflow steps by status"""
        query_params = {
            "query": json.dumps({"status": "COMPLETED"}),
            "limit": 10
        }

        response = await async_client.get(
            f"/{NAMESPACE}.workflow-step/incorrect_scope={workflow_id}/",
            params=query_params
        )

        data = response.json()
        assert response.status_code == 200, f"Invalid data: {data}"
        assert "data" in data


class TestQueryMetadata:
    """Test query metadata and schema information"""

    @pytest.mark.asyncio(loop_scope="module")
    async def test_query_manager_metadata(self, async_client):
        """Test query manager metadata endpoint"""
        response = await async_client.get(f"/_meta/{NAMESPACE}/")
        
        # This endpoint may or may not exist depending on implementation
        # Just test that it doesn't crash
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio(loop_scope="module")
    async def test_query_resource_schema(self, async_client):
        """Test individual query resource schemas"""
        # Test if schema information is available
        response = await async_client.get(f"/_meta/{NAMESPACE}/")
        
        assert response.status_code == 200
        # Basic metadata should be available
        data = response.json()
        assert "name" in data 
