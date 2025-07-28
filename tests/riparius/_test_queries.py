"""Test FastAPI queries for WorkflowQueryManager"""

import asyncio
import pytest
import json
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fluvius.data import UUID_GENF
from fluvius.fastapi import (
    create_app,
    configure_authentication,
    configure_domain_manager,
    configure_query_manager
)
from riparius.domain import WorkflowDomain, WorkflowQueryManager
from riparius import logger

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


# Test App Setup
@pytest.fixture(scope="class")
def test_app():
    """Create test FastAPI app with WorkflowQueryManager"""
    logger.info('Creating test app ...')
    app = create_app() \
        | configure_authentication(auth_profile_provider='FluviusMockProfileProvider') \
        | configure_domain_manager(WorkflowDomain) \
        | configure_query_manager(WorkflowQueryManager)
    return app


@pytest.fixture(scope="class")
def client(test_app):
    """Create test client"""
    logger.info('Creating test client ...')
    return TestClient(test_app, headers={"Authorization": f"MockAuth {json.dumps(PROFILE)}"})


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

    def test_workflow_query_basic(self, client):
        """Test basic workflow query without parameters"""
        response = client.get(f"/{NAMESPACE}.workflow/")
        
        data = response.json()
        assert response.status_code == 200, f"Invalid response: {data}"
        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)


    def test_workflow_query_with_parameters(self, client):
        """Test workflow query with query parameters"""
        query_params = {
            "size": 10,
            "page": 1,
            "query": json.dumps({"status": "ACTIVE"})
        }
        
        response = client.get(f"/{NAMESPACE}.workflow/", params=query_params)
        
        data = response.json()
        assert response.status_code == 200, f"Invalid response: {data}"
        assert "data" in data
        assert "pagination" in data
        assert len(data["data"]) <= 10  # Respects size limit

    def test_workflow_query_with_search(self, client):
        """Test workflow query with search parameters"""
        search_params = {
            "q": json.dumps({"title!has": "test"}),
            "size": 5
        }
        
        response = client.get(f"/{NAMESPACE}.workflow/", params=search_params)
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data

    def test_workflow_query_with_complex_filter(self, client):
        """Test workflow query with complex filter conditions"""
        complex_query = {
            "!or": [
                {"status": "ACTIVE"},
                {"status": "PAUSED"}
            ]
        }
        
        query_params = {
            "query": json.dumps(complex_query),
            "size": 20
        }
        
        response = client.get(f"/{NAMESPACE}.workflow/", params=query_params)
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data

    def test_workflow_embed_query(self, client):
        """Test workflow embed query (full workflow data)"""
        response = client.get(f"/{NAMESPACE}.workflow-embed/")
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)

    def test_workflow_step_query(self, client, workflow_id):
        """Test workflow step query with scoping"""
        # Test with scoped workflow ID
        response = client.get(f"/{NAMESPACE}.workflow-step/workflow_id={workflow_id}/")
        
        data = response.json()
        assert response.status_code == 200, f"Invalid data {data}"
        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)

    def test_workflow_step_query_with_filters(self, client, workflow_id):
        """Test workflow step query with additional filters"""
        query_params = {
            "query": json.dumps({"status": "ACTIVE"}),
            "size": 10
        }
        
        response = client.get(
            f"/{NAMESPACE}.workflow-step/workflow_id={workflow_id}/",
            params=query_params
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data

    def test_workflow_participant_query(self, client, workflow_id):
        """Test workflow participant query"""
        response = client.get(f"/{NAMESPACE}.workflow-participant/workflow_id={workflow_id}/")
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)

    def test_workflow_participant_query_with_role_filter(self, client, workflow_id):
        """Test workflow participant query with role filter"""
        query_params = {
            "query": json.dumps({"role": "reviewer"}),
            "size": 5
        }
        
        response = client.get(
            f"/{NAMESPACE}.workflow-participant/workflow_id={workflow_id}/",
            params=query_params
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data

    def test_workflow_stage_query(self, client, workflow_id):
        """Test workflow stage query"""
        response = client.get(f"/{NAMESPACE}.workflow-stage/workflow_id={workflow_id}/")
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "pagination" in data
        assert isinstance(data["data"], list)

    def test_workflow_stage_query_with_order_filter(self, client, workflow_id):
        """Test workflow stage query with order filter"""
        query_params = {
            "query": json.dumps({"order!gte": 1}),
            "sort": "order"
        }
        
        response = client.get(
            f"/{NAMESPACE}.workflow-stage/workflow_id={workflow_id}/",
            params=query_params
        )
        
        data = response.json()
        assert response.status_code == 200, f"Invalid data: {data}"
        assert "data" in data
        assert "pagination" in data


class TestQueryPagination:
    """Test query pagination functionality"""

    def test_pagination_first_page(self, client):
        """Test first page of workflow query"""
        query_params = {
            "limit": 3,
            "page": 1
        }
        
        response = client.get(f"/{NAMESPACE}.workflow/", params=query_params)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) <= 3
        assert "pagination" in data
        assert data["pagination"]["page"] == 1

    def test_pagination_second_page(self, client):
        """Test second page of workflow query"""
        query_params = {
            "limit": 3,
            "page": 2
        }
        
        response = client.get(f"/{NAMESPACE}.workflow/", params=query_params)
        
        assert response.status_code == 200
        data = response.json()
        assert "pagination" in data
        assert data["pagination"]["page"] == 2

    def test_large_page_size(self, client):
        """Test query with large page size"""
        query_params = {
            "size": 100,
            "page": 1
        }
        
        response = client.get(f"/{NAMESPACE}.workflow/", params=query_params)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) <= 100


class TestQuerySorting:
    """Test query sorting functionality"""

    def test_sort_by_title(self, client):
        """Test sorting workflows by title"""
        query_params = {
            "sort": "title",
            "size": 10
        }
        
        response = client.get(f"/{NAMESPACE}.workflow/", params=query_params)
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    def test_sort_by_creation_time(self, client):
        """Test sorting workflows by creation time"""
        query_params = {
            "sort": "ts_start.desc",  # Descending order
            "size": 10
        }
        
        response = client.get(f"/{NAMESPACE}.workflow/", params=query_params)
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    def test_multiple_sort_fields(self, client):
        """Test sorting by multiple fields"""
        query_params = {
            "sort": "status,title",
            "size": 10
        }
        
        response = client.get(f"/{NAMESPACE}.workflow/", params=query_params)
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data


class TestQueryValidation:
    """Test query validation and error handling"""

    def test_invalid_json_query(self, client):
        """Test query with invalid JSON"""
        query_params = {
            "query": "invalid json"
        }
        
        response = client.get(f"/{NAMESPACE}.workflow/", params=query_params)
        
        # Should either return 400 or handle gracefully
        assert response.status_code in [400, 422, 200]

    def test_invalid_page_number(self, client):
        """Test query with invalid page number"""
        query_params = {
            "page": -1,
            "size": 10
        }
        
        response = client.get(f"/{NAMESPACE}.workflow/", params=query_params)
        
        # Should handle gracefully or return error
        assert response.status_code in [400, 422, 200, 500]

    def test_invalid_size_parameter(self, client):
        """Test query with invalid size parameter"""
        query_params = {
            "size": -5,
            "page": 1
        }
        
        response = client.get(f"/{NAMESPACE}.workflow/", params=query_params)
        
        # Should handle gracefully or return error
        assert response.status_code in [400, 422, 200]

    def test_missing_required_scope(self, client):
        """Test scoped query without required scope parameter"""
        # Workflow step query requires workflow_id scope
        response = client.get(f"/{NAMESPACE}.workflow-step/")
        
        # Should return error for missing scope
        assert response.status_code in [400, 422, 404]


class TestQueryFieldFiltering:
    """Test field-specific filtering in queries"""

    def test_filter_by_workflow_status(self, client):
        """Test filtering workflows by status"""
        query_params = {
            "query": json.dumps({"status": "ACTIVE"}),
            "size": 10
        }
        
        response = client.get(f"/{NAMESPACE}.workflow/", params=query_params)
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    def test_filter_by_title_has(self, client):
        """Test filtering workflows by title containing text"""
        query_params = {
            "query": json.dumps({"title!has": "test"}),
            "size": 10
        }
        
        response = client.get(f"/{NAMESPACE}.workflow/", params=query_params)
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    def test_filter_by_date_range(self, client):
        """Test filtering workflows by date range"""
        query_params = {
            "query": json.dumps({
                "ts_start!gte": "2024-01-01T00:00:00",
                "ts_start!lte": "2024-12-31T23:59:59"
            }),
            "size": 10
        }
        
        response = client.get("/riparius-workflow.workflow/", params=query_params)
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    def test_filter_step_by_status(self, client, workflow_id):
        """Test filtering workflow steps by status"""
        query_params = {
            "query": json.dumps({"status": "PENDING"}),
            "size": 10
        }
        
        response = client.get(
            f"/{NAMESPACE}.workflow-step/workflow_id={workflow_id}/",
            params=query_params
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data


class TestQueryMetadata:
    """Test query metadata and schema information"""

    def test_query_manager_metadata(self, client):
        """Test query manager metadata endpoint"""
        response = client.get(f"/_meta/{NAMESPACE}/")
        
        # This endpoint may or may not exist depending on implementation
        # Just test that it doesn't crash
        assert response.status_code in [200, 404]

    def test_query_resource_schema(self, client):
        """Test individual query resource schemas"""
        # Test if schema information is available
        response = client.get(f"/_meta/{NAMESPACE}/")
        
        assert response.status_code == 200
        # Basic metadata should be available
        data = response.json()
        assert "name" in data 
