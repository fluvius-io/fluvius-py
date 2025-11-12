"""
Tests for workflow query endpoints
"""

import pytest
from httpx import AsyncClient


class TestWorkflowQueries:
    """Test workflow query operations"""

    async def test_list_workflows(self, client: AsyncClient):
        """Test listing workflows"""
        response = await client.get("/api/v1/workflow/workflow")
        
        # Should return 200 with list of workflows
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))
        
        # If it's a paginated response, check for expected structure
        if isinstance(data, dict):
            assert "items" in data or "results" in data

    async def test_get_workflow_by_id(self, client: AsyncClient):
        """Test getting a specific workflow by ID"""
        workflow_id = "550e8400-e29b-41d4-a716-446655440000"
        response = await client.get(f"/api/v1/workflow/workflow/{workflow_id}")
        
        # Should return 200 (found) or 404 (not found)
        assert response.status_code in [200, 404]

    async def test_list_workflow_steps(self, client: AsyncClient):
        """Test listing workflow steps"""
        response = await client.get("/api/v1/workflow/workflow-step")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))

    async def test_list_workflow_participants(self, client: AsyncClient):
        """Test listing workflow participants"""
        response = await client.get("/api/v1/workflow/workflow-participant")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))

    async def test_list_workflow_stages(self, client: AsyncClient):
        """Test listing workflow stages"""
        response = await client.get("/api/v1/workflow/workflow-stage")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, (list, dict))

    async def test_workflow_query_with_filters(self, client: AsyncClient):
        """Test workflow queries with filters"""
        # Test with status filter
        response = await client.get("/api/v1/workflow/workflow?status=ACTIVE")
        assert response.status_code == 200
        
        # Test with title search
        response = await client.get("/api/v1/workflow/workflow?title=Test")
        assert response.status_code == 200

    async def test_workflow_step_query_with_filters(self, client: AsyncClient):
        """Test workflow step queries with filters"""
        # Test with workflow_id filter
        workflow_id = "550e8400-e29b-41d4-a716-446655440000"
        response = await client.get(f"/api/v1/workflow/workflow-step?workflow_id={workflow_id}")
        assert response.status_code == 200
        
        # Test with status filter
        response = await client.get("/api/v1/workflow/workflow-step?status=ACTIVE")
        assert response.status_code == 200

    async def test_pagination(self, client: AsyncClient):
        """Test query pagination"""
        # Test with limit and offset
        response = await client.get("/api/v1/workflow/workflow?limit=10&offset=0")
        assert response.status_code == 200
        
        data = response.json()
        # Should handle pagination parameters gracefully
        assert isinstance(data, (list, dict))

    async def test_sorting(self, client: AsyncClient):
        """Test query sorting"""
        # Test with sort parameter
        response = await client.get("/api/v1/workflow/workflow?sort=created")
        assert response.status_code == 200
        
        # Test with reverse sort
        response = await client.get("/api/v1/workflow/workflow?sort=-created")
        assert response.status_code == 200

    async def test_invalid_query_parameters(self, client: AsyncClient):
        """Test handling of invalid query parameters"""
        # Test with invalid filter
        response = await client.get("/api/v1/workflow/workflow?invalid_param=value")
        # Should either ignore invalid params or return 400
        assert response.status_code in [200, 400]
        
        # Test with invalid ID format
        response = await client.get("/api/v1/workflow/workflow/invalid-id-format")
        assert response.status_code in [400, 404, 422] 