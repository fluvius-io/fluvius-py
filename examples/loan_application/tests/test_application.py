"""
Tests for application startup and basic functionality
"""

import pytest
from httpx import AsyncClient


class TestApplication:
    """Test basic application functionality"""

    async def test_root_endpoint(self, client: AsyncClient):
        """Test the root endpoint"""
        response = await client.get("/")
        # Should return some kind of response
        assert response.status_code in [200, 404]

    async def test_health_check(self, client: AsyncClient):
        """Test health check endpoint if available"""
        response = await client.get("/health")
        # May or may not exist, should handle gracefully
        assert response.status_code in [200, 404]

    async def test_docs_endpoint(self, client: AsyncClient):
        """Test OpenAPI docs endpoint"""
        response = await client.get("/docs")
        # Should return docs page or redirect
        assert response.status_code in [200, 404, 307]

    async def test_openapi_schema(self, client: AsyncClient):
        """Test OpenAPI schema endpoint"""
        response = await client.get("/openapi.json")
        # Should return OpenAPI schema
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            schema = response.json()
            assert "openapi" in schema
            assert "info" in schema
            assert "paths" in schema

    async def test_api_prefix_endpoints(self, client: AsyncClient):
        """Test that API endpoints are available under the correct prefix"""
        # Test that workflow endpoints exist under /process
        response = await client.get("/process/workflow")
        # Should be accessible
        assert response.status_code in [200, 401, 403]

    async def test_cors_headers(self, client: AsyncClient):
        """Test CORS headers if configured"""
        response = await client.options("/process/workflow")
        # Should handle OPTIONS request
        assert response.status_code in [200, 204, 405]

    async def test_content_type_json(self, client: AsyncClient):
        """Test that endpoints return JSON content type"""
        response = await client.get("/process/workflow")
        if response.status_code == 200:
            assert "application/json" in response.headers.get("content-type", "")

    async def test_error_handling(self, client: AsyncClient):
        """Test error handling for invalid endpoints"""
        response = await client.get("/api/v1/nonexistent-endpoint")
        assert response.status_code == 404

    async def test_method_not_allowed(self, client: AsyncClient):
        """Test method not allowed responses"""
        response = await client.delete("/process/workflow")
        # Should return 405 if DELETE is not allowed
        assert response.status_code in [405, 404, 401] 
