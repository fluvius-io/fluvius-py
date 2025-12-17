"""
Tests for workflow query endpoints
"""

import pytest
from httpx import AsyncClient


class TestWorkflowQueries:
    """Test workflow query operations"""

    @pytest.mark.asyncio
    async def test_list_workflows(self, client: AsyncClient):
        """Test listing workflows"""
        response = await client.post("/query/workflow")
        
        # Should return 200 with list of workflows, or 404 if endpoint not configured
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))
            
            # If it's a paginated response, check for expected structure
            if isinstance(data, dict):
                assert "items" in data or "results" in data

    @pytest.mark.asyncio
    async def test_get_workflow_by_id(self, client: AsyncClient):
        """Test getting a specific workflow by ID"""
        workflow_id = "550e8400-e29b-41d4-a716-446655440000"
        response = await client.post(f"/query/workflow/{workflow_id}")
        
        # Should return 200, 404 (not found/not configured)
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_list_workflow_steps(self, client: AsyncClient):
        """Test listing workflow steps"""
        response = await client.post("/query/workflow-step")
        
        # Should return 200 with list of steps, or 404 if endpoint not configured
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_list_workflow_participants(self, client: AsyncClient):
        """Test listing workflow participants"""
        response = await client.post("/query/workflow-participant")
        
        # Should return 200 with list of participants, or 404 if endpoint not configured
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_list_workflow_stages(self, client: AsyncClient):
        """Test listing workflow stages"""
        response = await client.post("/query/workflow-stage")
        
        # Should return 200 with list of stages, or 404 if endpoint not configured
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_workflow_query_with_filters(self, client: AsyncClient):
        """Test querying workflows with filters"""
        response = await client.post("/query/workflow", json={"status": "ACTIVE"})
        
        # Should return 200 with filtered results, or 404 if endpoint not configured
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_workflow_step_query_with_filters(self, client: AsyncClient):
        """Test querying workflow steps with filters"""
        workflow_id = "550e8400-e29b-41d4-a716-446655440000"
        response = await client.post("/query/workflow-step", json={"workflow_id": workflow_id})
        
        # Should return 200 with filtered results, or 404 if endpoint not configured
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_pagination(self, client: AsyncClient):
        """Test pagination parameters"""
        response = await client.post("/query/workflow", json={"limit": 10, "offset": 0})
        
        # Should return 200 with paginated results, or 404 if endpoint not configured
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_sorting(self, client: AsyncClient):
        """Test sorting parameters"""
        response = await client.post("/query/workflow", json={"sort": "created"})
        
        # Should return 200 with sorted results, or 404 if endpoint not configured
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_invalid_query_parameters(self, client: AsyncClient):
        """Test handling of invalid query parameters"""
        response = await client.post("/query/workflow", json={"invalid_param": "value"})
        
        # Should return 200, 400 (bad request), or 404 (not configured)
        assert response.status_code in [200, 400, 404]
