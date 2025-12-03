import pytest
from pytest import mark
from fluvius.form import FormDomain
from fluvius.form.schema import FormConnector
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


async def create_test_template_with_elements(domain):
    """Helper to create a template with section, form, element group, and element definitions"""
    template_id = UUID_GENR()
    template_key = f"test-template-{str(template_id)[:8]}"
    
    async with domain.statemgr.transaction():
        # Create template
        template = domain.statemgr.create(
            "template",
            _id=template_id,
            template_key=template_key,
            template_name="Test Template",
            desc="A test template for element tests",
            version=1,
            organization_id=FIXTURE_ORGANIZATION_ID,
        )
        await domain.statemgr.insert(template)
        
        # Create section definition
        section_def_id = UUID_GENR()
        section_def = domain.statemgr.create(
            "section_definition",
            _id=section_def_id,
            template_id=template_id,
            section_key=f"section-{str(section_def_id)[:8]}",
            section_name="Test Section",
            order=0,
        )
        await domain.statemgr.insert(section_def)
        
        # Create form definition
        form_def_id = UUID_GENR()
        form_def = domain.statemgr.create(
            "form_definition",
            _id=form_def_id,
            section_definition_id=section_def_id,
            form_key=f"form-{str(form_def_id)[:8]}",
            title="Test Form",
            order=0,
        )
        await domain.statemgr.insert(form_def)
        
        # Create element group definition
        group_def_id = UUID_GENR()
        group_def = domain.statemgr.create(
            "element_group_definition",
            _id=group_def_id,
            form_definition_id=form_def_id,
            group_key=f"group-{str(group_def_id)[:8]}",
            group_name="Test Group",
            order=0,
        )
        await domain.statemgr.insert(group_def)
        
        # Create element type
        element_type_id = UUID_GENR()
        element_type_key = f"text-input-{str(element_type_id)[:8]}"
        element_type = domain.statemgr.create(
            "element_type",
            _id=element_type_id,
            type_key=element_type_key,
            type_name="Text Input",
            desc="A text input element",
        )
        await domain.statemgr.insert(element_type)
        
        # Create element definition
        element_def_id = UUID_GENR()
        element_key = f"element-{str(element_def_id)[:8]}"
        element_def = domain.statemgr.create(
            "element_definition",
            _id=element_def_id,
            element_group_definition_id=group_def_id,
            element_type_id=element_type_id,
            element_key=element_key,
            element_label="Test Element",
            order=0,
            required=False,
        )
        await domain.statemgr.insert(element_def)
    
    return {
        "template_id": template_id,
        "template_key": template_key,
        "section_def_id": section_def_id,
        "form_def_id": form_def_id,
        "group_def_id": group_def_id,
        "element_type_id": element_type_id,
        "element_type_key": element_type_key,
        "element_def_id": element_def_id,
        "element_key": element_key,
    }


async def create_document_with_instances(domain, template_data, collection_id=None):
    """Helper to create a document with instances from a template"""
    from fluvius.form.element import ElementDataManager
    
    # Create collection if not provided
    if collection_id is None:
        collection_id = UUID_GENR()
        collection_key = f"test-collection-{str(collection_id)[:8]}"
        await command_handler(
            domain, "create-collection",
            {"collection_key": collection_key, "collection_name": "Test Collection", "organization_id": FIXTURE_ORGANIZATION_ID},
            "collection", collection_id
        )
    
    # Create document
    document_id = UUID_GENR()
    document_key = f"test-document-{str(document_id)[:8]}"
    payload = {
        "template_id": template_data["template_id"],
        "document_key": document_key,
        "document_name": "Test Document",
        "collection_id": collection_id,
        "organization_id": FIXTURE_ORGANIZATION_ID,
    }
    await command_handler(
        domain, "create-document", payload, "document", document_id
    )
    
    # Get section instance
    async with domain.statemgr.transaction():
        section_instances = await domain.statemgr.query(
            'section_instance',
            where={'document_id': document_id}
        )
        section_instance = section_instances[0] if section_instances else None
    
    # Get form instance
    element_data_mgr = ElementDataManager()
    form_instance = None
    element_group_instance = None
    
    if section_instance:
        async with element_data_mgr.transaction():
            form_instances = await element_data_mgr.query(
                'form_instance',
                where={'section_instance_id': section_instance._id}
            )
            form_instance = form_instances[0] if form_instances else None
            
            if form_instance:
                element_group_instances = await element_data_mgr.query(
                    'element_group_instance',
                    where={'form_instance_id': form_instance._id}
                )
                element_group_instance = element_group_instances[0] if element_group_instances else None
    
    return {
        "document_id": document_id,
        "collection_id": collection_id,
        "section_instance": section_instance,
        "form_instance": form_instance,
        "element_group_instance": element_group_instance,
    }


@mark.asyncio
async def test_element_type_creation(domain):
    """Test creating element types"""
    element_type_id = UUID_GENR()
    type_key = f"test-type-{str(element_type_id)[:8]}"
    
    async with domain.statemgr.transaction():
        element_type = domain.statemgr.create(
            "element_type",
            _id=element_type_id,
            type_key=type_key,
            type_name="Test Type",
            desc="A test element type",
        )
        await domain.statemgr.insert(element_type)
        
        fetched = await domain.statemgr.fetch('element_type', element_type_id)
        assert fetched.type_key == type_key
        assert fetched.type_name == "Test Type"


@mark.asyncio
async def test_element_definition_creation(domain):
    """Test creating element definitions"""
    template_data = await create_test_template_with_elements(domain)
    
    async with domain.statemgr.transaction():
        element_def = await domain.statemgr.fetch('element_definition', template_data["element_def_id"])
        assert element_def.element_group_definition_id == template_data["group_def_id"]
        assert element_def.element_type_id == template_data["element_type_id"]
        assert element_def.element_key == template_data["element_key"]
        assert element_def.element_label == "Test Element"
        assert element_def.order == 0
        assert element_def.required is False


@mark.asyncio
async def test_form_instance_creation(domain):
    """Test creating form instances via document creation"""
    template_data = await create_test_template_with_elements(domain)
    doc_data = await create_document_with_instances(domain, template_data)
    
    assert doc_data["form_instance"] is not None
    assert doc_data["form_instance"].form_definition_id == template_data["form_def_id"]
    assert doc_data["form_instance"].locked is False


@mark.asyncio
async def test_element_group_instance_creation(domain):
    """Test creating element group instances via document creation"""
    template_data = await create_test_template_with_elements(domain)
    doc_data = await create_document_with_instances(domain, template_data)
    
    assert doc_data["element_group_instance"] is not None
    assert doc_data["element_group_instance"].element_group_definition_id == template_data["group_def_id"]
    assert doc_data["element_group_instance"].form_instance_id == doc_data["form_instance"]._id


@mark.asyncio
async def test_element_instance_creation(domain):
    """Test creating element instances"""
    from fluvius.form.element import ElementDataManager
    
    template_data = await create_test_template_with_elements(domain)
    doc_data = await create_document_with_instances(domain, template_data)
    
    element_data_mgr = ElementDataManager()
    
    # Create element instance manually
    element_instance_id = UUID_GENR()
    instance_key = f"instance-{str(element_instance_id)[:8]}"
    
    async with element_data_mgr.transaction():
        element_instance = element_data_mgr.create(
            "element_instance",
            _id=element_instance_id,
            element_group_instance_id=doc_data["element_group_instance"]._id,
            element_definition_id=template_data["element_def_id"],
            instance_key=instance_key,
            data={"value": "test data"},
        )
        await element_data_mgr.insert(element_instance)
        
        fetched = await element_data_mgr.fetch('element_instance', element_instance_id)
        assert fetched.element_group_instance_id == doc_data["element_group_instance"]._id
        assert fetched.element_definition_id == template_data["element_def_id"]
        assert fetched.instance_key == instance_key
        assert fetched.data == {"value": "test data"}


@mark.asyncio
async def test_element_definition_resource_fields(domain):
    """Test that element definitions can have resource_name and resource_id fields"""
    template_data = await create_test_template_with_elements(domain)
    resource_id = UUID_GENR()
    
    async with domain.statemgr.transaction():
        element_def_id = UUID_GENR()
        element_key = f"element-resource-{str(element_def_id)[:8]}"
        element_def = domain.statemgr.create(
            "element_definition",
            _id=element_def_id,
            element_group_definition_id=template_data["group_def_id"],
            element_type_id=template_data["element_type_id"],
            element_key=element_key,
            element_label="Element with Resource",
            order=1,
            required=False,
            resource_id=resource_id,
            resource_name="test-resource",
        )
        await domain.statemgr.insert(element_def)
        
        fetched = await domain.statemgr.fetch('element_definition', element_def_id)
        assert fetched.resource_id == resource_id
        assert fetched.resource_name == "test-resource"


@mark.asyncio
async def test_multiple_element_definitions_in_group(domain):
    """Test creating multiple element definitions in an element group"""
    template_data = await create_test_template_with_elements(domain)
    
    async with domain.statemgr.transaction():
        # Create additional element definitions
        for i in range(3):
            element_def_id = UUID_GENR()
            element_def = domain.statemgr.create(
                "element_definition",
                _id=element_def_id,
                element_group_definition_id=template_data["group_def_id"],
                element_type_id=template_data["element_type_id"],
                element_key=f"element-{i}-{str(element_def_id)[:8]}",
                element_label=f"Test Element {i}",
                order=i + 1,
                required=False,
            )
            await domain.statemgr.insert(element_def)
        
        # Query all element definitions in the group
        element_defs = await domain.statemgr.query(
            'element_definition',
            where={'element_group_definition_id': template_data["group_def_id"]}
        )
        # Should have original + 3 new ones
        assert len(element_defs) >= 4


@mark.asyncio
async def test_multiple_element_groups_in_form(domain):
    """Test creating multiple element groups in a form definition"""
    template_data = await create_test_template_with_elements(domain)
    
    async with domain.statemgr.transaction():
        # Create additional element groups
        for i in range(2):
            group_def_id = UUID_GENR()
            group_def = domain.statemgr.create(
                "element_group_definition",
                _id=group_def_id,
                form_definition_id=template_data["form_def_id"],
                group_key=f"group-{i}-{str(group_def_id)[:8]}",
                group_name=f"Test Group {i}",
                order=i + 1,
            )
            await domain.statemgr.insert(group_def)
        
        # Query all element groups in the form
        group_defs = await domain.statemgr.query(
            'element_group_definition',
            where={'form_definition_id': template_data["form_def_id"]}
        )
        # Should have original + 2 new ones
        assert len(group_defs) >= 3


@mark.asyncio
async def test_form_instance_locking(domain):
    """Test that form instances can be locked"""
    from fluvius.form.element import ElementDataManager
    
    template_data = await create_test_template_with_elements(domain)
    doc_data = await create_document_with_instances(domain, template_data)
    
    element_data_mgr = ElementDataManager()
    
    # Verify form instance is not locked initially
    async with element_data_mgr.transaction():
        form_instance = await element_data_mgr.fetch('form_instance', doc_data["form_instance"]._id)
        assert form_instance.locked is False
        
        # Lock the form instance
        await element_data_mgr.update(form_instance, locked=True)
        
        # Verify it's locked
        form_instance = await element_data_mgr.fetch('form_instance', doc_data["form_instance"]._id)
        assert form_instance.locked is True


@mark.asyncio
async def test_element_type_with_schema(domain):
    """Test creating element types with element_schema"""
    element_type_id = UUID_GENR()
    type_key = f"test-type-schema-{str(element_type_id)[:8]}"
    
    async with domain.statemgr.transaction():
        element_type = domain.statemgr.create(
            "element_type",
            _id=element_type_id,
            type_key=type_key,
            type_name="Test Type with Schema",
            desc="A test element type with schema",
            element_schema={"type": "object", "properties": {"value": {"type": "string"}}},
            attrs={"custom": "attribute"},
        )
        await domain.statemgr.insert(element_type)
        
        fetched = await domain.statemgr.fetch('element_type', element_type_id)
        assert fetched.type_key == type_key
        assert fetched.element_schema is not None
        assert fetched.attrs == {"custom": "attribute"}
