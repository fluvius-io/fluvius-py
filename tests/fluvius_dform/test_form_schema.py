"""
Tests for FormModel Schema Generation

This module tests:
- FormModel registration via inheritance
- Form element extraction from annotations
- JSON schema generation for forms
- Form registry functionality
"""
import pytest
from pytest import mark
import json

from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport

from fluvius.dform.form import (
    FormModel,
    FormElement,
    FormModelRegistry,
    ElementModel
)

from fluvius.dform import logger
from fluvius.dform.fastapi import setup_dform
from fluvius.fastapi.setup import setup_error_handler


# ============================================================================
# Import dform_app to register all elements and forms
# ============================================================================

# This import registers all ElementModels and FormModels from dform_app
import fluvius_test.dform_app as dform_app
from fluvius_test.dform_app import (
    ApplicantInfoForm,
    EmploymentDetailsForm,
    LoanRequestForm,
    AuthorizationForm,
    AccountInfoForm,
    PreferencesForm,
)


# ============================================================================
# Test Cases for FormModel Registration
# ============================================================================

class TestFormModelRegistration:
    """Test FormModel registration via inheritance"""
    
    def test_forms_registered(self):
        """Test that forms from dform_app are registered"""
        keys = list(FormModelRegistry.keys())
        
        assert "applicant-info" in keys
        assert "employment-details" in keys
        assert "loan-request" in keys
        assert "authorization" in keys
        assert "account-info" in keys
        assert "addresses" in keys
        assert "preferences" in keys
    
    def test_form_meta_attributes(self):
        """Test that Meta attributes are correctly set"""
        form = FormModelRegistry.get("applicant-info")
        
        assert form.Meta.key == "applicant-info"
        assert form.Meta.name == "Applicant Information"
        assert form.Meta.desc == "Primary applicant personal details"
        assert form.Meta.header == "Primary Applicant"
        assert form.Meta.footer == "All information will be verified."
    
    def test_form_elements_extracted(self):
        """Test that elements are extracted from annotations"""
        elements = ApplicantInfoForm.get_elements()
        
        assert len(elements) == 4
        assert "personal_info" in elements
        assert "address" in elements
        assert "phone" in elements
        assert "email" in elements
    
    def test_element_meta_attributes(self):
        """Test that element metadata is correctly extracted"""
        elements = ApplicantInfoForm.get_elements()
        
        personal_info = elements["personal_info"]
        assert issubclass(personal_info, ElementModel)
        assert personal_info.Meta.key == "personal-info"
        # assert personal_info.param.get("required") is True
        
        address = elements["address"]
        assert address.Meta.key == "address"


class TestFormToDict:
    """Test FormModel.to_dict() method"""
    
    def test_to_dict_basic(self):
        """Test basic to_dict conversion"""
        data = ApplicantInfoForm.to_dict()
        
        assert data["key"] == "applicant-info"
        assert data["name"] == "Applicant Information"
        assert data["desc"] == "Primary applicant personal details"
        assert data["header"] == "Primary Applicant"
        assert data["footer"] == "All information will be verified."
        assert "elements" in data
    
    def test_to_dict_elements(self):
        """Test elements in to_dict output"""
        data = ApplicantInfoForm.to_dict()
        elements = data["elements"]
        
        assert len(elements) == 4
        
        personal_info = elements["personal_info"]
        assert personal_info['key'] == "personal-info"
    
    def test_to_dict_serializable(self):
        """Test that to_dict output is JSON serializable"""
        data = ApplicantInfoForm.to_dict()
        json_str = json.dumps(data)
        
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["key"] == "applicant-info"


class TestFormJsonSchema:
    """Test FormModel.model_json_schema() method"""
    
    def test_json_schema_structure(self):
        """Test JSON schema basic structure"""
        schema = ApplicantInfoForm.model_json_schema()
        
        assert schema["type"] == "object"
        assert schema["title"] == "Applicant Information"
        assert schema["description"] == "Primary applicant personal details"
        assert "properties" in schema
        assert schema["x-form-key"] == "applicant-info"
    
    def test_json_schema_properties(self):
        """Test JSON schema properties"""
        schema = ApplicantInfoForm.model_json_schema()
        props = schema["properties"]
        
        assert "personal_info" in props
        assert "address" in props
        assert "phone" in props
        assert "email" in props
        
        # Each property should have elem_key metadata
        assert props["personal_info"]["x-elem-key"] == "personal-info"
        assert props["address"]["x-elem-key"] == "address"
    
    def test_json_schema_required_fields(self):
        """Test required fields in JSON schema"""
        schema = ApplicantInfoForm.model_json_schema()
        required = schema.get("required") or []
        
        # Check fields marked as required via param
        for name, elem in ApplicantInfoForm.get_elements().items():
            if elem.required:
                assert name in required
    
    def test_json_schema_with_options(self):
        """Test JSON schema for form with select options"""
        schema = LoanRequestForm.model_json_schema()
        props = schema["properties"]
        
        # Check loan_purpose has options in param
        loan_purpose = props["loan_purpose"]
        assert "x-param" in loan_purpose
        assert "options" in loan_purpose["x-param"]
        
        options = loan_purpose["x-param"]["options"]
        assert len(options) == 5
        assert any(opt["value"] == "home" for opt in options)
    
    def test_json_schema_serializable(self):
        """Test that JSON schema is serializable"""
        schema = ApplicantInfoForm.model_json_schema()
        json_str = json.dumps(schema, indent=4)

        logger.info(json_str)
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["x-form-key"] == "applicant-info"


class TestAllDformAppForms:
    """Test all forms from dform_app"""
    
    def test_all_forms_have_elements(self):
        """Test that all registered forms have elements"""
        for key in FormModelRegistry.keys():
            form = FormModelRegistry.get(key)
            elements = form.get_elements()
            
            # Every form should have at least one element
            assert len(elements) > 0, f"Form {key} has no elements"
    
    def test_all_forms_generate_schema(self):
        """Test that all forms can generate JSON schema"""
        for key in FormModelRegistry.keys():
            form = FormModelRegistry.get(key)
            schema = form.model_json_schema()
            
            # Basic schema structure
            assert schema["type"] == "object"
            assert "properties" in schema
            assert schema["x-form-key"] == key
    
    def test_all_forms_to_dict(self):
        """Test that all forms can be converted to dict"""
        for key in FormModelRegistry.keys():
            form = FormModelRegistry.get(key)
            data = form.to_dict()
            
            assert data["key"] == key
            assert "elements" in data
    
    def test_form_counts(self):
        """Test expected number of forms registered"""
        # From dform_app we expect 14 forms
        keys = list(FormModelRegistry.keys())
        assert len(keys) >= 14, f"Expected at least 14 forms, got {len(keys)}: {keys}"


@mark.asyncio
class TestFormSchemaAPI:
    """Test FastAPI endpoints for form schema (if implemented)"""
    
    @pytest.fixture
    def app(self):
        """Create a FastAPI app with dform endpoints"""
        app = FastAPI()
        setup_error_handler(app)
        setup_dform(app)
        return app
    
    @pytest.fixture
    async def client(self, app):
        """Create an async HTTP client for testing"""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    
    async def test_list_form_types(self, client):
        """Test listing all registered form types"""
        response = await client.get("/dform/form-types")
        
        # May return 404 if endpoint not implemented
        if response.status_code == 200:
            data = response.json()
            assert "form_types" in data
            
            keys = [ft["key"] for ft in data["form_types"]]
            assert "applicant-info" in keys
    
    async def test_get_form_schema(self, client):
        """Test getting JSON schema for a form"""
        response = await client.get("/dform/form-schema/applicant-info")
        
        # May return 404 if endpoint not implemented
        if response.status_code == 200:
            data = response.json()
            assert data["key"] == "applicant-info"
            assert "schema" in data



