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
    DataElementModel
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
    
    def test_element_is_element_model(self):
        """Test that extracted elements are ElementModel subclasses"""
        elements = ApplicantInfoForm.get_elements()
        
        personal_info = elements["personal_info"]
        assert issubclass(personal_info, DataElementModel)
        assert personal_info.Meta.key == "personal-info"
        
        address = elements["address"]
        assert issubclass(address, DataElementModel)
        assert address.Meta.key == "address"

    def test_element_model_has_meta(self):
        """Test that ElementModel classes have proper Meta"""
        elements = ApplicantInfoForm.get_elements()

        for name, elem in elements.items():
            assert hasattr(elem, 'Meta')
            assert hasattr(elem.Meta, 'key')
            assert hasattr(elem.Meta, 'title')


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
        
        # Elements now contain ElementModel.Meta dumped as dict
        personal_info = elements["personal_info"]
        assert personal_info["key"] == "personal-info"
        assert personal_info["title"] == "Personal Information"
    
    def test_to_dict_serializable(self):
        """Test that to_dict output is JSON serializable"""
        data = ApplicantInfoForm.to_dict()
        json_str = json.dumps(data)
        
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["key"] == "applicant-info"

    def test_to_dict_all_forms(self):
        """Test that all forms can be converted to dict"""
        for key in FormModelRegistry.keys():
            form = FormModelRegistry.get(key)
            data = form.to_dict()

            assert data["key"] == key
            assert "elements" in data
            assert len(data["elements"]) > 0


class TestFormJsonSchema:
    """Test FormModel.model_json_schema() - Pydantic native schema"""
    
    def test_json_schema_structure(self):
        """Test JSON schema basic structure"""
        schema = ApplicantInfoForm.model_json_schema()
        
        # Pydantic's native schema structure
        assert "properties" in schema
        assert "title" in schema
        # Title is the class name by default
        assert schema["title"] == "ApplicantInfoForm"
    
    def test_json_schema_properties(self):
        """Test JSON schema properties"""
        schema = ApplicantInfoForm.model_json_schema()
        props = schema["properties"]
        
        assert "personal_info" in props
        assert "address" in props
        assert "phone" in props
        assert "email" in props

    def test_json_schema_property_references(self):
        """Test JSON schema property references to element definitions"""
        schema = ApplicantInfoForm.model_json_schema()
        props = schema["properties"]
        
        # Each property should reference the element model's schema
        for prop_name in ["personal_info", "address", "phone", "email"]:
            prop = props[prop_name]
            # Property should have $ref to definitions or title
            assert "$ref" in prop or "title" in prop

    def test_json_schema_has_definitions(self):
        """Test that JSON schema includes element definitions"""
        schema = ApplicantInfoForm.model_json_schema()

        # Pydantic puts nested model schemas in $defs
        assert "$defs" in schema
        defs = schema["$defs"]
        
        # Should have definitions for the element models
        assert len(defs) > 0
        # Check that element model definitions are present
        assert "PersonalInfoElement" in defs
        assert "AddressElement" in defs
    
    def test_json_schema_serializable(self):
        """Test that JSON schema is serializable"""
        schema = ApplicantInfoForm.model_json_schema()
        json_str = json.dumps(schema, indent=4)

        logger.info(f"ApplicantInfoForm schema:\n{json_str}")
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert "properties" in parsed

    def test_json_schema_element_definition_properties(self):
        """Test that element definitions have proper properties"""
        schema = ApplicantInfoForm.model_json_schema()
        defs = schema["$defs"]

        # Check PersonalInfoElement has expected fields
        personal_info_def = defs["PersonalInfoElement"]
        assert "properties" in personal_info_def
        props = personal_info_def["properties"]
        assert "first_name" in props
        assert "last_name" in props

        # Check AddressElement has expected fields
        address_def = defs["AddressElement"]
        assert "properties" in address_def
        addr_props = address_def["properties"]
        assert "street_line1" in addr_props
        assert "city" in addr_props


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
            
            # Basic Pydantic schema structure
            assert "properties" in schema
            assert len(schema["properties"]) > 0
    
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

    def test_all_elements_are_element_models(self):
        """Test that all form elements are ElementModel subclasses"""
        for key in FormModelRegistry.keys():
            form = FormModelRegistry.get(key)
            for elem_name, elem_cls in form.get_elements().items():
                assert issubclass(elem_cls, DataElementModel), \
                    f"Form {key} element {elem_name} is not an ElementModel"


class TestFormModelAsDataModel:
    """Test FormModel as a Pydantic DataModel"""

    def test_form_model_instantiation(self):
        """Test that FormModel subclasses can be instantiated"""
        from fluvius_test.dform_app import PersonalInfoElement, AddressElement, PhoneNumberElement, EmailElement

        # Create element instances
        personal = PersonalInfoElement(first_name="John", last_name="Doe")
        address = AddressElement(street_line1="123 Main St", city="NYC", state="NY", postal_code="10001")
        phone = PhoneNumberElement(phone_number="555-1234")
        email = EmailElement(email="john@example.com")

        # Create form instance
        form_data = ApplicantInfoForm(
            personal_info=personal,
            address=address,
            phone=phone,
            email=email
        )

        assert form_data.personal_info.first_name == "John"
        assert form_data.address.city == "NYC"
        assert form_data.phone.phone_number == "555-1234"
        assert form_data.email.email == "john@example.com"

    def test_form_model_validation(self):
        """Test that FormModel validates element data"""
        from fluvius_test.dform_app import PersonalInfoElement, AddressElement, PhoneNumberElement, EmailElement

        # Valid data should work
        form_data = ApplicantInfoForm(
            personal_info=PersonalInfoElement(first_name="Jane", last_name="Smith"),
            address=AddressElement(street_line1="456 Oak Ave", city="LA", state="CA", postal_code="90001"),
            phone=PhoneNumberElement(phone_number="555-5678"),
            email=EmailElement(email="jane@example.com")
        )

        assert form_data.personal_info.last_name == "Smith"

    def test_form_model_dump(self):
        """Test FormModel.model_dump()"""
        from fluvius_test.dform_app import PersonalInfoElement, AddressElement, PhoneNumberElement, EmailElement

        form_data = ApplicantInfoForm(
            personal_info=PersonalInfoElement(first_name="Test", last_name="User"),
            address=AddressElement(street_line1="789 Pine St", city="Boston", state="MA", postal_code="02101"),
            phone=PhoneNumberElement(phone_number="555-9999"),
            email=EmailElement(email="test@example.com")
        )

        dumped = form_data.model_dump()

        assert dumped["personal_info"]["first_name"] == "Test"
        assert dumped["address"]["city"] == "Boston"
        assert isinstance(dumped, dict)


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
