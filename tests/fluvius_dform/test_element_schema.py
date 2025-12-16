"""
Tests for Element Schema Registration and FastAPI Endpoints

This module tests:
- Creating custom elements by inheriting ElementModel
- Registering element schemas
- Querying element JSON schemas via the FastAPI endpoint
"""
import pytest
from pytest import mark
from typing import Optional, List
from pydantic import Field

from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from fluvius.dform.element import (
    ElementModel, 
    ElementModelRegistry,
)
from fluvius.dform.fastapi import setup_dform
from fluvius.fastapi.setup import setup_error_handler


# ============================================================================
# Sample Element Definitions for Testing
# ============================================================================

class TextInputElementModel(ElementModel):
    """A simple text input element"""
    value: str = Field(default="", description="The text input value")
    placeholder: Optional[str] = Field(default=None, description="Placeholder text")
    max_length: Optional[int] = Field(default=None, description="Maximum character length")
    
    class Meta:
        key = "text-input"
        name = "Text Input"
        desc = "A single-line text input element"
        table_name = "text_input_element"


class NumberInputElementModel(ElementModel):
    """A number input element with min/max bounds"""
    value: float = Field(default=0.0, description="The numeric value")
    min_value: Optional[float] = Field(default=None, description="Minimum allowed value")
    max_value: Optional[float] = Field(default=None, description="Maximum allowed value")
    step: Optional[float] = Field(default=1.0, description="Step increment")
    
    class Meta:
        key = "number-input"
        name = "Number Input"
        desc = "A numeric input element with optional bounds"
        table_name = "number_input_element"


class SelectElementModel(ElementModel):
    """A select/dropdown element"""
    value: str = Field(default="", description="The selected value")
    options: List[str] = Field(default_factory=list, description="Available options")
    allow_multiple: bool = Field(default=False, description="Allow multiple selections")
    
    class Meta:
        key = "select"
        name = "Select"
        desc = "A dropdown selection element"
        table_name = "select_element"


# ============================================================================
# Test Cases
# ============================================================================

class TestElementRegistration:
    """Test element registration via ElementModel inheritance"""
    
    def test_element_registration(self):
        """Test that elements are registered in the registry"""
        assert "text-input" in ElementModelRegistry.keys()
        assert "number-input" in ElementModelRegistry.keys()
        assert "select" in ElementModelRegistry.keys()
    
    def test_element_meta_attributes(self):
        """Test that Meta attributes are correctly set"""
        text_input = ElementModelRegistry.get("text-input")
        assert text_input.Meta.key == "text-input"
        assert text_input.Meta.name == "Text Input"
        assert text_input.Meta.desc == "A single-line text input element"
        assert text_input.Meta.table_name == "text_input_element"
    
    def test_element_model_is_pydantic(self):
        """Test that ElementModel is a valid Pydantic model"""
        text_input = ElementModelRegistry.get("text-input")
        assert hasattr(text_input, 'model_json_schema')
        
        # Create an instance to verify the model works
        data = text_input(value="hello", placeholder="Enter text")
        assert data.value == "hello"
        assert data.placeholder == "Enter text"
    
    def test_element_model_json_schema(self):
        """Test that ElementModel produces valid JSON schema"""
        text_input = ElementModelRegistry.get("text-input")
        schema = text_input.model_json_schema()
        
        assert "properties" in schema
        assert "value" in schema["properties"]
        assert "placeholder" in schema["properties"]
        assert "max_length" in schema["properties"]
    
    def test_element_schema_auto_generated(self):
        """Test that SQLAlchemy Schema is auto-generated from the model"""
        text_input = ElementModelRegistry.get("text-input")
        assert text_input.Schema is not None
        assert hasattr(text_input.Schema, '__tablename__')
        assert text_input.Schema.__tablename__ == "text_input_element"


@mark.asyncio
class TestElementSchemaAPI:
    """Test FastAPI endpoints for element schema"""
    
    @pytest.fixture
    def app(self):
        """Create a FastAPI app with dform endpoints"""
        app = FastAPI()
        setup_error_handler(app)  # Add error handlers for proper HTTP responses
        setup_dform(app)
        return app
    
    @pytest.fixture
    async def client(self, app):
        """Create an async HTTP client for testing"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    
    async def test_list_element_types(self, client):
        """Test listing all registered element types"""
        response = await client.get("/dform/element-types")
        assert response.status_code == 200
        
        data = response.json()
        assert "element_types" in data
        
        # Find our registered elements
        keys = [et["key"] for et in data["element_types"]]
        assert "text-input" in keys
        assert "number-input" in keys
        assert "select" in keys
    
    async def test_get_element_schema_text_input(self, client):
        """Test getting JSON schema for text-input element"""
        response = await client.get("/dform/element-schema/text-input")
        assert response.status_code == 200
        
        data = response.json()
        assert data["key"] == "text-input"
        assert data["name"] == "Text Input"
        assert data["desc"] == "A single-line text input element"
        assert "schema" in data
        
        # Verify JSON schema structure
        schema = data["schema"]
        assert "properties" in schema
        assert "value" in schema["properties"]
    
    async def test_get_element_schema_number_input(self, client):
        """Test getting JSON schema for number-input element"""
        response = await client.get("/dform/element-schema/number-input")
        assert response.status_code == 200
        
        data = response.json()
        assert data["key"] == "number-input"
        assert "schema" in data
        
        schema = data["schema"]
        assert "value" in schema["properties"]
        assert "min_value" in schema["properties"]
        assert "max_value" in schema["properties"]
        assert "step" in schema["properties"]
    
    async def test_get_element_schema_select(self, client):
        """Test getting JSON schema for select element"""
        response = await client.get("/dform/element-schema/select")
        assert response.status_code == 200
        
        data = response.json()
        assert data["key"] == "select"
        
        schema = data["schema"]
        assert "value" in schema["properties"]
        assert "options" in schema["properties"]
        assert "allow_multiple" in schema["properties"]
    
    async def test_get_element_schema_not_found(self, client):
        """Test getting schema for non-existent element type"""
        response = await client.get("/dform/element-schema/non-existent")
        assert response.status_code == 404  # NotFoundError returns 404


class TestElementModelValidation:
    """Test element model data validation"""
    
    def test_text_input_validation(self):
        """Test TextInputElementModel validation"""
        # Valid data
        data = TextInputElementModel(value="hello world")
        assert data.value == "hello world"
        
        # With optional fields
        data = TextInputElementModel(value="test", placeholder="Enter text", max_length=100)
        assert data.placeholder == "Enter text"
        assert data.max_length == 100
    
    def test_number_input_validation(self):
        """Test NumberInputElementModel validation"""
        data = NumberInputElementModel(value=42.5, min_value=0, max_value=100)
        assert data.value == 42.5
        assert data.min_value == 0
        assert data.max_value == 100
    
    def test_select_validation(self):
        """Test SelectElementModel validation"""
        data = SelectElementModel(
            value="option1",
            options=["option1", "option2", "option3"],
            allow_multiple=True
        )
        assert data.value == "option1"
        assert len(data.options) == 3
        assert data.allow_multiple is True
    
    def test_model_serialization(self):
        """Test model serialization to dict"""
        data = TextInputElementModel(value="test", placeholder="hint")
        serialized = data.model_dump()
        
        assert serialized["value"] == "test"
        assert serialized["placeholder"] == "hint"
        assert serialized.get("max_length") is None
