import pytest
from pytest import mark
from fluvius.form import FormDomain
from fluvius.form.model import FormConnector
from fluvius.data import UUID_GENR
from fluvius.domain.context import DomainTransport


FIXTURE_REALM = "fluvius-form-testing"
FIXTURE_USER_ID = UUID_GENR()
FIXTURE_ORGANIZATION_ID = "05e8bb7e-43e6-4766-98d9-8f8c779dbe45"
FIXTURE_PROFILE_ID = UUID_GENR()


async def command_handler(domain, cmd_key, payload, resource, identifier, scope=None, context=None):
    scope = scope or {}
    context = context or {}
    _context = dict(
        headers=dict(),
        transport=DomainTransport.FASTAPI,
        source="fluvius-form-test",
        realm=FIXTURE_REALM,
        user_id=FIXTURE_USER_ID,
        organization_id=FIXTURE_ORGANIZATION_ID,
        profile_id=FIXTURE_PROFILE_ID
    )
    if context:
        _context.update(**context)

    with domain.session(None, **_context):
        command = domain.create_command(
            cmd_key,
            payload,
            aggroot=(
                resource,
                identifier,
                scope.get('domain_sid'),
                scope.get('domain_iid'),
            )
        )

        return await domain.process_command(command)


# Domain and setup_db fixtures are now in conftest.py
# setup_db runs once per session to preserve data for inspection


async def create_test_form_with_element(domain):
    """Helper to create a form with an element"""
    form_id = UUID_GENR()
    element_type_id = UUID_GENR()
    element_id = UUID_GENR()
    
    async with domain.statemgr.transaction():
        form = domain.statemgr.create(
            "data_form",
            _id=form_id,
            form_key="test-form",
            form_name="Test Form",
            version=1,
            organization_id=FIXTURE_ORGANIZATION_ID,
        )
        await domain.statemgr.insert(form)
        
        element_type = domain.statemgr.create(
            "element_type",
            _id=element_type_id,
            type_key="text-input",
            type_name="Text Input",
            desc="A text input element",
        )
        await domain.statemgr.insert(element_type)
        
        element = domain.statemgr.create(
            "data_element",
            _id=element_id,
            form_id=form_id,
            element_type_id=element_type_id,
            element_key="test-element",
            element_label="Test Element",
            order=0,
            required=False,
        )
        await domain.statemgr.insert(element)
    
    return form_id, element_id, element_type_id


@mark.asyncio
async def test_element_type_creation(domain):
    """Test creating element types"""

    element_type_id = UUID_GENR()
    async with domain.statemgr.transaction():
        element_type = domain.statemgr.create(
            "element_type",
            _id=element_type_id,
            type_key="test-type",
            type_name="Test Type",
            desc="A test element type",
        )
        await domain.statemgr.insert(element_type)
        
        fetched = await domain.statemgr.fetch('element_type', element_type_id)
        assert fetched.type_key == "test-type"
        assert fetched.type_name == "Test Type"


@mark.asyncio
async def test_data_element_creation(domain):
    """Test creating data elements"""

    form_id, element_id, element_type_id = await create_test_form_with_element(domain)
    
    async with domain.statemgr.transaction():
        element = await domain.statemgr.fetch('data_element', element_id)
        assert element.form_id == form_id
        assert element.element_type_id == element_type_id
        assert element.element_key == "test-element"
        assert element.element_label == "Test Element"
        assert element.order == 0
        assert element.required is False


@mark.asyncio
async def test_form_instance_creation(domain):
    """Test creating form instances"""

    form_id, _, _ = await create_test_form_with_element(domain)
    form_instance_id = UUID_GENR()
    
    from fluvius.form.element import ElementDataManager
    element_data_mgr = ElementDataManager()
    
    async with element_data_mgr.transaction():
        form_instance = element_data_mgr.create("form_instance",
            _id=form_instance_id,
            form_id=form_id,
            instance_key=f"instance-{str(form_instance_id)[:8]}", instance_name=None, organization_id=FIXTURE_ORGANIZATION_ID,
        )
        await element_data_mgr.insert(form_instance)
        
        fetched = await element_data_mgr.fetch('form_instance', form_instance_id)
        assert fetched.form_id == form_id
        assert fetched.organization_id == FIXTURE_ORGANIZATION_ID
        assert fetched.locked is False


@mark.asyncio
async def test_save_element_with_data(domain):
    """Test saving element data to a form instance"""

    form_id, element_id, _ = await create_test_form_with_element(domain)
    form_instance_id = UUID_GENR()
    
    from fluvius.form.element import ElementDataManager
    element_data_mgr = ElementDataManager()
    
    # Create form instance
    async with element_data_mgr.transaction():
        form_instance = element_data_mgr.create("form_instance",
            _id=form_instance_id,
            form_id=form_id,
            instance_key=f"instance-{str(form_instance_id)[:8]}", instance_name=None, organization_id=FIXTURE_ORGANIZATION_ID,
        )
        await element_data_mgr.insert(form_instance)
        form_instance = await element_data_mgr.fetch('form_instance', form_instance_id)

    # Save element data
    save_payload = {
        "element_id": element_id,
        "form_instance_id": form_instance_id,
        "data": {"value": "test data value"},
    }
    result = await command_handler(
        domain, "save-element", save_payload, "data_element", element_id
    )
    assert result is not None


@mark.asyncio
async def test_save_form_multiple_elements(domain):
    """Test saving form data with multiple elements"""

    form_id, element_id, element_type_id = await create_test_form_with_element(domain)
    
    # Create another element
    element_id_2 = UUID_GENR()
    async with domain.statemgr.transaction():
        element_2 = domain.statemgr.create(
            "data_element",
            _id=element_id_2,
            form_id=form_id,
            element_type_id=element_type_id,
            element_key="test-element-2",
            element_label="Test Element 2",
            order=1,
            required=False,
        )
        await domain.statemgr.insert(element_2)

    form_instance_id = UUID_GENR()
    from fluvius.form.element import ElementDataManager
    element_data_mgr = ElementDataManager()
    
    # Create form instance
    async with element_data_mgr.transaction():
        form_instance = element_data_mgr.create("form_instance",
            _id=form_instance_id,
            form_id=form_id,
            instance_key=f"instance-{str(form_instance_id)[:8]}", instance_name=None, organization_id=FIXTURE_ORGANIZATION_ID,
        )
        await element_data_mgr.insert(form_instance)
        form_instance = await element_data_mgr.fetch('form_instance', form_instance_id)

    # Save form with multiple elements
    save_payload = {
        "form_id": form_id,
        "form_instance_id": form_instance_id,
        "elements": [
            {"element_id": element_id, "data": {"value": "value 1"}},
            {"element_id": element_id_2, "data": {"value": "value 2"}},
        ],
    }
    result = await command_handler(
        domain, "save-form", save_payload, "data_form", form_id
    )
    assert result is not None


@mark.asyncio
async def test_submit_form_locks_instance(domain):
    """Test that submitting a form locks the form instance"""

    form_id, element_id, _ = await create_test_form_with_element(domain)
    form_instance_id = UUID_GENR()
    
    from fluvius.form.element import ElementDataManager
    element_data_mgr = ElementDataManager()
    
    # Create form instance
    async with element_data_mgr.transaction():
        form_instance = element_data_mgr.create("form_instance",
            _id=form_instance_id,
            form_id=form_id,
            instance_key=f"instance-{str(form_instance_id)[:8]}", instance_name=None, organization_id=FIXTURE_ORGANIZATION_ID,
        )
        await element_data_mgr.insert(form_instance)
        form_instance = await element_data_mgr.fetch('form_instance', form_instance_id)
        assert form_instance.locked is False

    # Submit form
    submit_payload = {
        "form_id": form_id,
        "form_instance_id": form_instance_id,
        "elements": [
            {"element_id": element_id, "data": {"value": "submitted value"}},
        ],
    }
    result = await command_handler(
        domain, "submit-form", submit_payload, "data_form", form_id
    )
    assert result is not None
    
    # Verify form instance is locked
    async with element_data_mgr.transaction():
        form_instance = await element_data_mgr.fetch('form_instance', form_instance_id)
        assert form_instance.locked is True


@mark.asyncio
async def test_element_resource_fields(domain):
    """Test that elements can have resource_name and resource_id fields"""

    form_id, _, element_type_id = await create_test_form_with_element(domain)
    element_id = UUID_GENR()
    resource_id = UUID_GENR()
    
    async with domain.statemgr.transaction():
        element = domain.statemgr.create(
            "data_element",
            _id=element_id,
            form_id=form_id,
            element_type_id=element_type_id,
            element_key="test-element-resource",
            element_label="Test Element with Resource",
            order=0,
            required=False,
            resource_id=resource_id,
            resource_name="test-resource",
        )
        await domain.statemgr.insert(element)
        
        fetched = await domain.statemgr.fetch('data_element', element_id)
        assert fetched.resource_id == resource_id
        assert fetched.resource_name == "test-resource"

