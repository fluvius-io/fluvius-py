import pytest
from pytest import mark
from fluvius.dform import FormDomain
from fluvius.dform.schema import FormConnector
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
        # Create collection first (required for template)
        collection_id = UUID_GENR()
        collection = domain.statemgr.create(
            "collection",
            _id=collection_id,
            collection_key=f"test-collection-{str(collection_id)[:8]}",
            collection_name="Test Collection",
            organization_id=FIXTURE_ORGANIZATION_ID,
        )
        await domain.statemgr.insert(collection)
        
        # Create template
        template = domain.statemgr.create(
            "template",
            _id=template_id,
            template_key=template_key,
            template_name="Test Template",
            desc="A test template for element tests",
            version=1,
            organization_id=FIXTURE_ORGANIZATION_ID,
            collection_id=collection_id,
        )
        await domain.statemgr.insert(template)
        
        # Create section definition
        section_def_id = UUID_GENR()
        section_key = f"section-{str(section_def_id)[:8]}"
        section_def = domain.statemgr.create(
            "template_section",
            _id=section_def_id,
            template_id=template_id,
            section_key=section_key,
            section_name="Test Section",
            order=0,
        )
        await domain.statemgr.insert(section_def)
        
        # Create form definition (standalone)
        form_def_id = UUID_GENR()
        form_key = f"form-{str(form_def_id)[:8]}"
        form_def = domain.statemgr.create(
            "form_definition",
            _id=form_def_id,
            form_key=form_key,
            title="Test Form",
            desc="A test form",
        )
        await domain.statemgr.insert(form_def)
        
        # Link form to template via TemplateForm
        template_form_def = domain.statemgr.create(
            "template_form",
            _id=UUID_GENR(),
            template_id=template_id,
            form_id=form_def_id,
            section_key=section_key,
        )
        await domain.statemgr.insert(template_form_def)
        
        # Create element group definition
        group_def_id = UUID_GENR()
        group_key = f"group-{str(group_def_id)[:8]}"
        group_def = domain.statemgr.create(
            "form_element_group",
            _id=group_def_id,
            form_definition_id=form_def_id,
            group_key=group_key,
            group_name="Test Group",
            order=0,
        )
        await domain.statemgr.insert(group_def)
        
        # Create element definition (standalone with element_schema)
        element_def_id = UUID_GENR()
        element_key = f"element-{str(element_def_id)[:8]}"
        element_def = domain.statemgr.create(
            "element_definition",
            _id=element_def_id,
            element_key=element_key,
            element_label="Test Element",
            element_schema={"type": "text", "placeholder": "Enter text"},
        )
        await domain.statemgr.insert(element_def)
        
        # Link element to form via FormElement
        form_element_def = domain.statemgr.create(
            "form_element",
            _id=UUID_GENR(),
            form_definition_id=form_def_id,
            group_key=group_key,
            element_key=element_key,
            order=0,
            required=False,
        )
        await domain.statemgr.insert(form_element_def)
    
    return {
        "template_id": template_id,
        "template_key": template_key,
        "collection_id": collection_id,
        "section_def_id": section_def_id,
        "section_key": section_key,
        "form_def_id": form_def_id,
        "form_key": form_key,
        "group_def_id": group_def_id,
        "group_key": group_key,
        "element_def_id": element_def_id,
        "element_key": element_key,
    }


@mark.asyncio
async def test_element_definition_creation(domain):
    """Test creating element definitions"""
    template_data = await create_test_template_with_elements(domain)
    
    async with domain.statemgr.transaction():
        element_def = await domain.statemgr.fetch('element_definition', template_data["element_def_id"])
        assert element_def.element_key == template_data["element_key"]
        assert element_def.element_label == "Test Element"
        assert element_def.element_schema is not None
        assert element_def.element_schema["type"] == "text"


@mark.asyncio
async def test_element_definition_with_complex_schema(domain):
    """Test that element definitions can have complex element_schema"""
    async with domain.statemgr.transaction():
        element_def_id = UUID_GENR()
        element_key = f"element-complex-{str(element_def_id)[:8]}"
        element_schema = {
            "type": "select",
            "options": [
                {"value": "opt1", "label": "Option 1"},
                {"value": "opt2", "label": "Option 2"},
            ],
            "default": "opt1",
            "validation": {"required": True},
        }
        element_def = domain.statemgr.create(
            "element_definition",
            _id=element_def_id,
            element_key=element_key,
            element_label="Element with Complex Schema",
            element_schema=element_schema,
        )
        await domain.statemgr.insert(element_def)
        
        fetched = await domain.statemgr.fetch('element_definition', element_def_id)
        assert fetched.element_schema["type"] == "select"
        assert len(fetched.element_schema["options"]) == 2


@mark.asyncio
async def test_multiple_element_definitions(domain):
    """Test creating multiple element definitions"""
    template_data = await create_test_template_with_elements(domain)
    
    async with domain.statemgr.transaction():
        # Create additional element definitions
        for i in range(3):
            element_def_id = UUID_GENR()
            element_key = f"element-{i}-{str(element_def_id)[:8]}"
            element_def = domain.statemgr.create(
                "element_definition",
                _id=element_def_id,
                element_key=element_key,
                element_label=f"Test Element {i}",
                element_schema={"type": "text", "order": i + 1},
            )
            await domain.statemgr.insert(element_def)
            
            # Link to form via FormElement
            form_element_def = domain.statemgr.create(
                "form_element",
                _id=UUID_GENR(),
                form_definition_id=template_data["form_def_id"],
                group_key=template_data["group_key"],
                element_key=element_key,
                order=i + 1,
                required=False,
            )
            await domain.statemgr.insert(form_element_def)
        
        # Query form element definitions for this form
        form_elem_defs = await domain.statemgr.query(
            'form_element',
            where={'form_definition_id': template_data["form_def_id"]}
        )
        # Should have original + 3 new ones
        assert len(form_elem_defs) >= 4


@mark.asyncio
async def test_multiple_element_groups_in_form(domain):
    """Test creating multiple element groups in a form definition"""
    template_data = await create_test_template_with_elements(domain)
    
    async with domain.statemgr.transaction():
        # Create additional element groups
        for i in range(2):
            group_def_id = UUID_GENR()
            group_def = domain.statemgr.create(
                "form_element_group",
                _id=group_def_id,
                form_definition_id=template_data["form_def_id"],
                group_key=f"group-{i}-{str(group_def_id)[:8]}",
                group_name=f"Test Group {i}",
                order=i + 1,
            )
            await domain.statemgr.insert(group_def)
        
        # Query all element groups in the form
        group_defs = await domain.statemgr.query(
            'form_element_group',
            where={'form_definition_id': template_data["form_def_id"]}
        )
        # Should have original + 2 new ones
        assert len(group_defs) >= 3


@mark.asyncio
async def test_element_definition_various_schema_types(domain):
    """Test creating element definitions with various schema types"""
    async with domain.statemgr.transaction():
        # Text input
        text_id = UUID_GENR()
        text_def = domain.statemgr.create(
            "element_definition",
            _id=text_id,
            element_key=f"text-{str(text_id)[:8]}",
            element_label="Text Input",
            element_schema={"type": "text", "maxLength": 100},
        )
        await domain.statemgr.insert(text_def)
        
        # Number input
        number_id = UUID_GENR()
        number_def = domain.statemgr.create(
            "element_definition",
            _id=number_id,
            element_key=f"number-{str(number_id)[:8]}",
            element_label="Number Input",
            element_schema={"type": "number", "min": 0, "max": 100},
        )
        await domain.statemgr.insert(number_def)
        
        # Checkbox
        checkbox_id = UUID_GENR()
        checkbox_def = domain.statemgr.create(
            "element_definition",
            _id=checkbox_id,
            element_key=f"checkbox-{str(checkbox_id)[:8]}",
            element_label="Checkbox",
            element_schema={"type": "boolean", "default": False},
        )
        await domain.statemgr.insert(checkbox_def)
        
        # Verify all were created
        text_fetched = await domain.statemgr.fetch('element_definition', text_id)
        assert text_fetched.element_schema["type"] == "text"
        
        number_fetched = await domain.statemgr.fetch('element_definition', number_id)
        assert number_fetched.element_schema["type"] == "number"
        
        checkbox_fetched = await domain.statemgr.fetch('element_definition', checkbox_id)
        assert checkbox_fetched.element_schema["type"] == "boolean"
