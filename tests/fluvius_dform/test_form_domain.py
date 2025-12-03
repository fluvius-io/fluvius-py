import pytest
from pytest import mark
from sqlalchemy import text
from uuid import UUID
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


async def create_test_template(domain, collection_id=None):
    """Helper to create a test template with section, form, element group, and element definitions"""
    template_id = UUID_GENR()
    template_key = f"test-template-{str(template_id)[:8]}"
    
    async with domain.statemgr.transaction():
        # Create collection first if not provided (required for template)
        if collection_id is None:
            collection_id = UUID_GENR()
            collection = domain.statemgr.create(
                "collection",
                _id=collection_id,
                collection_key=f"test-collection-{str(collection_id)[:8]}",
                collection_name="Test Collection",
                desc="Auto-created collection for template",
                organization_id=FIXTURE_ORGANIZATION_ID,
            )
            await domain.statemgr.insert(collection)
        
        # Create template (requires collection_id)
        template = domain.statemgr.create(
            "template",
            _id=template_id,
            template_key=template_key,
            template_name="Test Template",
            desc="A test template",
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
            desc="A test section",
            order=0,
        )
        await domain.statemgr.insert(section_def)
        
        # Create form definition (standalone, linked via TemplateForm)
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
            desc="A test element group",
            order=0,
        )
        await domain.statemgr.insert(group_def)
        
        # Create element definition (standalone, linked via FormElement)
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


# ============================================================================
# COLLECTION TESTS
# ============================================================================

@mark.asyncio
async def test_create_collection(domain):
    """Test creating a collection"""
    collection_id = UUID_GENR()
    collection_key = f"test-collection-{str(collection_id)[:8]}"
    payload = {
        "collection_key": collection_key,
        "collection_name": "Test Collection",
        "desc": "A test collection",
        "organization_id": FIXTURE_ORGANIZATION_ID,
    }
    result = await command_handler(
        domain, "create-collection", payload, "collection", collection_id
    )
    
    async with domain.statemgr.transaction():
        collection = await domain.statemgr.fetch('collection', collection_id)
        assert collection.collection_key == collection_key
        assert collection.collection_name == "Test Collection"
        assert collection.desc == "A test collection"
        assert collection.organization_id == FIXTURE_ORGANIZATION_ID


@mark.asyncio
async def test_update_collection(domain):
    """Test updating a collection"""
    collection_id = UUID_GENR()
    collection_key = f"test-collection-{str(collection_id)[:8]}"
    create_payload = {
        "collection_key": collection_key,
        "collection_name": "Test Collection",
        "organization_id": FIXTURE_ORGANIZATION_ID,
    }
    await command_handler(
        domain, "create-collection", create_payload, "collection", collection_id
    )
    
    update_payload = {
        "collection_name": "Updated Collection Name",
        "desc": "Updated description",
    }
    result = await command_handler(
        domain, "update-collection", update_payload, "collection", collection_id
    )
    
    async with domain.statemgr.transaction():
        collection = await domain.statemgr.fetch('collection', collection_id)
        assert collection.collection_name == "Updated Collection Name"
        assert collection.desc == "Updated description"


@mark.asyncio
async def test_remove_collection(domain):
    """Test removing a collection"""
    collection_id = UUID_GENR()
    collection_key = f"test-collection-{str(collection_id)[:8]}"
    create_payload = {
        "collection_key": collection_key,
        "collection_name": "Test Collection",
        "organization_id": FIXTURE_ORGANIZATION_ID,
    }
    await command_handler(
        domain, "create-collection", create_payload, "collection", collection_id
    )
    
    remove_payload = {}
    result = await command_handler(
        domain, "remove-collection", remove_payload, "collection", collection_id
    )
    
    async with domain.statemgr.transaction():
        collection = await domain.statemgr.find_one('collection', identifier=collection_id)
        assert collection is None


# ============================================================================
# DOCUMENT TESTS (Documents are instances of Templates)
# ============================================================================

@mark.asyncio
async def test_create_document(domain):
    """Test creating a document from a template and adding it to a collection"""
    # First create a template
    template_data = await create_test_template(domain)

    # Create a collection
    collection_id = UUID_GENR()
    collection_key = f"test-collection-for-doc-{str(collection_id)[:8]}"
    collection_payload = {
        "collection_key": collection_key,
        "collection_name": "Test Collection",
        "organization_id": FIXTURE_ORGANIZATION_ID,
    }
    await command_handler(
        domain, "create-collection", collection_payload, "collection", collection_id
    )

    # Now create a document from template in the collection
    document_id = UUID_GENR()
    document_key = f"test-document-{str(document_id)[:8]}"
    payload = {
        "template_id": template_data["template_id"],
        "document_key": document_key,
        "document_name": "Test Document",
        "collection_id": collection_id,
        "desc": "A test document",
        "version": 1,
        "order": 0,
        "organization_id": FIXTURE_ORGANIZATION_ID,
        "resource_id": UUID_GENR(),
        "resource_name": "test-resource",
    }
    result = await command_handler(
        domain, "create-document", payload, "document", document_id
    )
    
    async with domain.statemgr.transaction():
        document = await domain.statemgr.fetch('document', document_id)
        assert document.document_key == document_key
        assert document.document_name == "Test Document"
        assert document.template_id == template_data["template_id"]
        assert document.desc == "A test document"
        assert document.version == 1
        assert document.organization_id == FIXTURE_ORGANIZATION_ID
        assert document.resource_id is not None
        assert document.resource_name == "test-resource"
        
        # Verify document is in the collection
        doc_collections = await domain.statemgr.query(
            'document_collection',
            where={'document_id': document_id, 'collection_id': collection_id}
        )
        assert len(doc_collections) == 1
        assert doc_collections[0].order == 0
        
        # Verify section instances were created from template
        sections = await domain.statemgr.query(
            'document_section',
            where={'document_id': document_id}
        )
        assert len(sections) >= 1


@mark.asyncio
async def test_update_document(domain):
    """Test updating a document"""
    template_data = await create_test_template(domain)
    
    collection_id = UUID_GENR()
    collection_key = f"test-collection-for-update-{str(collection_id)[:8]}"
    await command_handler(
        domain, "create-collection",
        {"collection_key": collection_key, "collection_name": "Test Collection", "organization_id": FIXTURE_ORGANIZATION_ID},
        "collection", collection_id
    )

    document_id = UUID_GENR()
    document_key = f"test-document-{str(document_id)[:8]}"
    create_payload = {
        "template_id": template_data["template_id"],
        "document_key": document_key,
        "document_name": "Test Document",
        "collection_id": collection_id,
        "organization_id": FIXTURE_ORGANIZATION_ID,
    }
    await command_handler(
        domain, "create-document", create_payload, "document", document_id
    )
    
    update_payload = {
        "document_name": "Updated Document Name",
        "desc": "Updated description",
        "version": 2,
    }
    result = await command_handler(
        domain, "update-document", update_payload, "document", document_id
    )
    
    async with domain.statemgr.transaction():
        document = await domain.statemgr.fetch('document', document_id)
        assert document.document_name == "Updated Document Name"
        assert document.desc == "Updated description"
        assert document.version == 2


@mark.asyncio
async def test_remove_document(domain):
    """Test removing a document"""
    template_data = await create_test_template(domain)
    
    collection_id = UUID_GENR()
    collection_key = f"test-collection-for-remove-{str(collection_id)[:8]}"
    await command_handler(
        domain, "create-collection",
        {"collection_key": collection_key, "collection_name": "Test Collection", "organization_id": FIXTURE_ORGANIZATION_ID},
        "collection", collection_id
    )

    document_id = UUID_GENR()
    document_key = f"test-document-{str(document_id)[:8]}"
    create_payload = {
        "template_id": template_data["template_id"],
        "document_key": document_key,
        "document_name": "Test Document",
        "collection_id": collection_id,
        "organization_id": FIXTURE_ORGANIZATION_ID,
    }
    await command_handler(
        domain, "create-document", create_payload, "document", document_id
    )
    
    remove_payload = {}
    result = await command_handler(
        domain, "remove-document", remove_payload, "document", document_id
    )
    
    async with domain.statemgr.transaction():
        document = await domain.statemgr.find_one('document', identifier=document_id)
        assert document is None


@mark.asyncio
async def test_move_document(domain):
    """Test moving a document between collections"""
    template_data = await create_test_template(domain)

    # Create source collection
    source_collection_id = UUID_GENR()
    source_collection_key = f"source-collection-move-{str(source_collection_id)[:8]}"
    await command_handler(
        domain, "create-collection",
        {"collection_key": source_collection_key, "collection_name": "Source Collection", "organization_id": FIXTURE_ORGANIZATION_ID},
        "collection", source_collection_id
    )

    # Create target collection
    target_collection_id = UUID_GENR()
    target_collection_key = f"target-collection-move-{str(target_collection_id)[:8]}"
    await command_handler(
        domain, "create-collection",
        {"collection_key": target_collection_key, "collection_name": "Target Collection", "organization_id": FIXTURE_ORGANIZATION_ID},
        "collection", target_collection_id
    )

    # Create a document in source collection
    document_id = UUID_GENR()
    document_key = f"document-to-move-{str(document_id)[:8]}"
    create_payload = {
        "template_id": template_data["template_id"],
        "document_key": document_key,
        "document_name": "Document to Move",
        "collection_id": source_collection_id,
        "organization_id": FIXTURE_ORGANIZATION_ID,
        "order": 0,
    }
    await command_handler(
        domain, "create-document", create_payload, "document", document_id
    )

    # Verify document is in source collection
    async with domain.statemgr.transaction():
        doc_collections = await domain.statemgr.query(
            'document_collection',
            where={'document_id': document_id, 'collection_id': source_collection_id}
        )
        assert len(doc_collections) == 1

    # Move document to target collection
    move_payload = {
        "target_collection_id": target_collection_id,
        "source_collection_id": source_collection_id,
        "order": 5,
    }
    result = await command_handler(
        domain, "move-document", move_payload, "document", document_id
    )

    # Verify document is now in target collection
    async with domain.statemgr.transaction():
        # Should not be in source collection anymore
        source_doc_collections = await domain.statemgr.query(
            'document_collection',
            where={'document_id': document_id, 'collection_id': source_collection_id}
        )
        assert len(source_doc_collections) == 0

        # Should be in target collection
        target_doc_collections = await domain.statemgr.query(
            'document_collection',
            where={'document_id': document_id, 'collection_id': target_collection_id}
        )
        assert len(target_doc_collections) == 1
        assert target_doc_collections[0].order == 5


@mark.asyncio
async def test_move_document_remove_from_all(domain):
    """Test moving a document by removing it from all collections"""
    template_data = await create_test_template(domain)

    # Create collection
    collection_id = UUID_GENR()
    collection_key = f"test-collection-remove-{str(collection_id)[:8]}"
    await command_handler(
        domain, "create-collection",
        {"collection_key": collection_key, "collection_name": "Test Collection", "organization_id": FIXTURE_ORGANIZATION_ID},
        "collection", collection_id
    )

    # Create a document in collection
    document_id = UUID_GENR()
    document_key = f"document-to-remove-{str(document_id)[:8]}"
    create_payload = {
        "template_id": template_data["template_id"],
        "document_key": document_key,
        "document_name": "Document to Remove",
        "collection_id": collection_id,
        "organization_id": FIXTURE_ORGANIZATION_ID,
    }
    await command_handler(
        domain, "create-document", create_payload, "document", document_id
    )

    # Create target collection
    target_collection_id = UUID_GENR()
    target_collection_key = f"target-collection-remove-{str(target_collection_id)[:8]}"
    await command_handler(
        domain, "create-collection",
        {"collection_key": target_collection_key, "collection_name": "Target Collection", "organization_id": FIXTURE_ORGANIZATION_ID},
        "collection", target_collection_id
    )

    # Move document to target collection (without specifying source)
    move_payload = {
        "target_collection_id": target_collection_id,
        "order": 0,
    }
    result = await command_handler(
        domain, "move-document", move_payload, "document", document_id
    )

    # Verify document is in target collection
    async with domain.statemgr.transaction():
        target_doc_collections = await domain.statemgr.query(
            'document_collection',
            where={'document_id': document_id, 'collection_id': target_collection_id}
        )
        assert len(target_doc_collections) == 1


@mark.asyncio
async def test_create_document_without_collection(domain):
    """Test creating a document without adding it to a collection"""
    template_data = await create_test_template(domain)

    document_id = UUID_GENR()
    document_key = f"test-document-no-collection-{str(document_id)[:8]}"
    payload = {
        "template_id": template_data["template_id"],
        "document_key": document_key,
        "document_name": "Test Document",
        "organization_id": FIXTURE_ORGANIZATION_ID,
    }
    
    result = await command_handler(
        domain, "create-document", payload, "document", document_id
    )
    
    async with domain.statemgr.transaction():
        document = await domain.statemgr.fetch('document', document_id)
        assert document.document_key == document_key
        assert document.document_name == "Test Document"
        
        # Verify document is not in any collection
        doc_collections = await domain.statemgr.query(
            'document_collection',
            where={'document_id': document_id}
        )
        assert len(doc_collections) == 0


# ============================================================================
# ELEMENT SCHEMA TESTS
# ============================================================================

@mark.asyncio
async def test_element_definition_schema_validation(domain):
    """Test creating element definitions with various schema types"""
    async with domain.statemgr.transaction():
        # Text input element
        text_elem_id = UUID_GENR()
        text_elem = domain.statemgr.create(
            "element_definition",
            _id=text_elem_id,
            element_key=f"text-{str(text_elem_id)[:8]}",
            element_label="Text Input",
            element_schema={"type": "text", "maxLength": 100},
        )
        await domain.statemgr.insert(text_elem)
        
        fetched = await domain.statemgr.fetch('element_definition', text_elem_id)
        assert fetched.element_schema["type"] == "text"
        assert fetched.element_schema["maxLength"] == 100


# ============================================================================
# SECTION DEFINITION TESTS
# ============================================================================

@mark.asyncio
async def test_template_section_creation(domain):
    """Test creating section definitions within a template"""
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
        
        template = domain.statemgr.create(
            "template",
            _id=template_id,
            template_key=template_key,
            template_name="Test Template",
            version=1,
            organization_id=FIXTURE_ORGANIZATION_ID,
            collection_id=collection_id,
        )
        await domain.statemgr.insert(template)
        
        section_def_id = UUID_GENR()
        section_key = f"section-{str(section_def_id)[:8]}"
        section_def = domain.statemgr.create(
            "template_section",
            _id=section_def_id,
            template_id=template_id,
            section_key=section_key,
            section_name="Test Section",
            desc="A test section definition",
            order=0,
        )
        await domain.statemgr.insert(section_def)
        
        fetched = await domain.statemgr.fetch('template_section', section_def_id)
        assert fetched.section_key == section_key
        assert fetched.section_name == "Test Section"
        assert fetched.template_id == template_id


# ============================================================================
# FORM DEFINITION TESTS
# ============================================================================

@mark.asyncio
async def test_form_definition_creation(domain):
    """Test creating form definitions and linking to template via TemplateForm"""
    template_data = await create_test_template(domain)
    
    async with domain.statemgr.transaction():
        form_def_id = UUID_GENR()
        form_key = f"form-{str(form_def_id)[:8]}"
        form_def = domain.statemgr.create(
            "form_definition",
            _id=form_def_id,
            form_key=form_key,
            title="Another Test Form",
            desc="Another test form definition",
        )
        await domain.statemgr.insert(form_def)
        
        # Link form to template via TemplateForm
        template_form_def = domain.statemgr.create(
            "template_form",
            _id=UUID_GENR(),
            template_id=template_data["template_id"],
            form_id=form_def_id,
            section_key=template_data["section_key"],
        )
        await domain.statemgr.insert(template_form_def)
        
        fetched = await domain.statemgr.fetch('form_definition', form_def_id)
        assert fetched.form_key == form_key
        assert fetched.title == "Another Test Form"


# ============================================================================
# ELEMENT GROUP DEFINITION TESTS
# ============================================================================

@mark.asyncio
async def test_form_element_group_creation(domain):
    """Test creating element group definitions within a form definition"""
    template_data = await create_test_template(domain)
    
    async with domain.statemgr.transaction():
        group_def_id = UUID_GENR()
        group_key = f"group-{str(group_def_id)[:8]}"
        group_def = domain.statemgr.create(
            "form_element_group",
            _id=group_def_id,
            form_definition_id=template_data["form_def_id"],
            group_key=group_key,
            group_name="Another Group",
            desc="Another test group",
            order=1,
        )
        await domain.statemgr.insert(group_def)
        
        fetched = await domain.statemgr.fetch('form_element_group', group_def_id)
        assert fetched.group_key == group_key
        assert fetched.group_name == "Another Group"
        assert fetched.form_definition_id == template_data["form_def_id"]


# ============================================================================
# ELEMENT DEFINITION TESTS
# ============================================================================

@mark.asyncio
async def test_element_definition_creation(domain):
    """Test creating element definitions and linking to form via FormElement"""
    template_data = await create_test_template(domain)
    
    async with domain.statemgr.transaction():
        element_def_id = UUID_GENR()
        element_key = f"element-{str(element_def_id)[:8]}"
        element_def = domain.statemgr.create(
            "element_definition",
            _id=element_def_id,
            element_key=element_key,
            element_label="Another Element",
            element_schema={"type": "number", "min": 0, "max": 100},
        )
        await domain.statemgr.insert(element_def)
        
        # Link element to form via FormElement
        form_element_def = domain.statemgr.create(
            "form_element",
            _id=UUID_GENR(),
            form_definition_id=template_data["form_def_id"],
            group_key=template_data["group_key"],
            element_key=element_key,
            order=1,
            required=True,
        )
        await domain.statemgr.insert(form_element_def)
        
        fetched = await domain.statemgr.fetch('element_definition', element_def_id)
        assert fetched.element_key == element_key
        assert fetched.element_label == "Another Element"
        
        # Verify the link was created
        form_elem_fetched = await domain.statemgr.find_one(
            'form_element',
            where={'element_key': element_key, 'form_definition_id': template_data["form_def_id"]}
        )
        assert form_elem_fetched.required is True
        assert form_elem_fetched.order == 1


@mark.asyncio
async def test_element_definition_with_schema(domain):
    """Test that element definitions can have complex element_schema"""
    template_data = await create_test_template(domain)
    
    async with domain.statemgr.transaction():
        element_def_id = UUID_GENR()
        element_key = f"element-{str(element_def_id)[:8]}"
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
        assert fetched.element_schema["default"] == "opt1"


@mark.asyncio
async def test_create_document_with_complex_template(domain):
    """Test creating a document from a template with multiple forms, groups, and elements"""
    template_id = UUID_GENR()
    template_key = f"complex-template-{str(template_id)[:8]}"
    
    async with domain.statemgr.transaction():
        # Create collection for template
        collection_id = UUID_GENR()
        collection = domain.statemgr.create(
            "collection",
            _id=collection_id,
            collection_key=f"collection-{str(collection_id)[:8]}",
            collection_name="Complex Template Collection",
            organization_id=FIXTURE_ORGANIZATION_ID,
        )
        await domain.statemgr.insert(collection)
        
        # Create template
        template = domain.statemgr.create(
            "template",
            _id=template_id,
            template_key=template_key,
            template_name="Complex Template",
            desc="A template with multiple forms, groups, and elements",
            version=1,
            organization_id=FIXTURE_ORGANIZATION_ID,
            collection_id=collection_id,
        )
        await domain.statemgr.insert(template)
        
        # Create 2 sections
        sections = []
        for i in range(2):
            section_id = UUID_GENR()
            section_key = f"section-{i}-{str(section_id)[:8]}"
            section = domain.statemgr.create(
                "template_section",
                _id=section_id,
                template_id=template_id,
                section_key=section_key,
                section_name=f"Section {i + 1}",
                desc=f"Section {i + 1} description",
                order=i,
            )
            await domain.statemgr.insert(section)
            sections.append({"id": section_id, "key": section_key})
        
        # Create 3 form definitions
        forms = []
        for i in range(3):
            form_id = UUID_GENR()
            form_key = f"form-{i}-{str(form_id)[:8]}"
            form_def = domain.statemgr.create(
                "form_definition",
                _id=form_id,
                form_key=form_key,
                title=f"Form {i + 1}",
                desc=f"Form {i + 1} description",
            )
            await domain.statemgr.insert(form_def)
            
            # Link form to template (forms 0,1 in section 0, form 2 in section 1)
            section_idx = 0 if i < 2 else 1
            template_form = domain.statemgr.create(
                "template_form",
                _id=UUID_GENR(),
                template_id=template_id,
                form_id=form_id,
                section_key=sections[section_idx]["key"],
            )
            await domain.statemgr.insert(template_form)
            
            forms.append({
                "id": form_id,
                "key": form_key,
                "section_key": sections[section_idx]["key"],
                "groups": [],
                "elements": [],
            })
        
        # Create element groups for each form (2-3 groups per form)
        for form_idx, form in enumerate(forms):
            num_groups = 2 if form_idx == 0 else 3
            for g in range(num_groups):
                group_id = UUID_GENR()
                group_key = f"group-{form_idx}-{g}-{str(group_id)[:8]}"
                group = domain.statemgr.create(
                    "form_element_group",
                    _id=group_id,
                    form_definition_id=form["id"],
                    group_key=group_key,
                    group_name=f"Group {g + 1} of Form {form_idx + 1}",
                    desc=f"Element group {g + 1}",
                    order=g,
                )
                await domain.statemgr.insert(group)
                form["groups"].append({"id": group_id, "key": group_key})
        
        # Create element definitions and link them to forms
        element_schemas = [
            {"type": "text", "placeholder": "Enter text"},
            {"type": "number", "min": 0, "max": 100},
            {"type": "select", "options": ["A", "B", "C"]},
            {"type": "checkbox", "label": "Agree?"},
            {"type": "date", "format": "YYYY-MM-DD"},
        ]
        
        element_counter = 0
        for form_idx, form in enumerate(forms):
            # Create 2-4 elements per form, distributed across groups
            num_elements = 2 + form_idx  # Form 0: 2 elements, Form 1: 3, Form 2: 4
            for e in range(num_elements):
                element_id = UUID_GENR()
                element_key = f"element-{form_idx}-{e}-{str(element_id)[:8]}"
                
                # Create element definition
                element_def = domain.statemgr.create(
                    "element_definition",
                    _id=element_id,
                    element_key=element_key,
                    element_label=f"Element {e + 1} of Form {form_idx + 1}",
                    element_schema=element_schemas[element_counter % len(element_schemas)],
                )
                await domain.statemgr.insert(element_def)
                
                # Link element to form via form_element
                group_idx = e % len(form["groups"])
                form_element = domain.statemgr.create(
                    "form_element",
                    _id=UUID_GENR(),
                    form_definition_id=form["id"],
                    group_key=form["groups"][group_idx]["key"],
                    element_key=element_key,
                    order=e,
                    required=(e == 0),  # First element of each form is required
                )
                await domain.statemgr.insert(form_element)
                
                form["elements"].append({
                    "id": element_id,
                    "key": element_key,
                    "group_key": form["groups"][group_idx]["key"],
                })
                element_counter += 1
    
    # Now create a document from this complex template
    document_id = UUID_GENR()
    document_key = f"complex-doc-{str(document_id)[:8]}"
    payload = {
        "template_id": template_id,
        "document_key": document_key,
        "document_name": "Complex Document",
        "collection_id": collection_id,
        "desc": "Document created from complex template",
        "version": 1,
        "organization_id": FIXTURE_ORGANIZATION_ID,
    }
    
    result = await command_handler(
        domain, "create-document", payload, "document", document_id
    )
    
    # Verify all structures were copied correctly
    async with domain.statemgr.transaction():
        # Verify document was created
        document = await domain.statemgr.fetch('document', document_id)
        assert document.document_key == document_key
        assert document.template_id == template_id
        
        # Verify document_sections were created (should be 2)
        doc_sections = await domain.statemgr.query(
            'document_section',
            where={'document_id': document_id},
            sort=(("order", "asc"),)
        )
        assert len(doc_sections) == 2
        assert doc_sections[0].section_key == sections[0]["key"]
        assert doc_sections[1].section_key == sections[1]["key"]
        
        # Verify form instances were created (should be 3)
        form_instances = await domain.statemgr.query(
            'document_form',
            where={'document_id': document_id}
        )
        assert len(form_instances) == 3
        
        # Verify form keys match
        form_keys = {f.form_key for f in form_instances}
        expected_form_keys = {f["key"] for f in forms}
        assert form_keys == expected_form_keys
        
        # Verify section_key assignments on forms
        for fi in form_instances:
            matching_form = next(f for f in forms if f["key"] == fi.form_key)
            assert fi.section_key == matching_form["section_key"]
        
        # Verify element group instances were created
        # Total groups: Form 0 has 2, Form 1 has 3, Form 2 has 3 = 8 groups
        total_groups = 0
        for fi in form_instances:
            groups = await domain.statemgr.query(
                'element_group',
                where={'form_id': fi._id}
            )
            matching_form = next(f for f in forms if f["key"] == fi.form_key)
            assert len(groups) == len(matching_form["groups"])
            total_groups += len(groups)
        assert total_groups == 8
        
        # Verify element instances were created
        # Total elements: Form 0 has 2, Form 1 has 3, Form 2 has 4 = 9 elements
        elements = await domain.statemgr.query(
            'element',
            where={'document_id': document_id}
        )
        assert len(elements) == 9
        
        # Verify element keys match
        element_keys = {e.element_key for e in elements}
        expected_element_keys = set()
        for f in forms:
            for elem in f["elements"]:
                expected_element_keys.add(elem["key"])
        assert element_keys == expected_element_keys
        
        # Verify elements are linked to correct forms and groups
        for elem in elements:
            # Find which form definition this element belongs to
            form_instance = await domain.statemgr.fetch('document_form', elem.form_id)
            matching_form = next(f for f in forms if f["key"] == form_instance.form_key)
            
            # Find the expected group_key for this element
            matching_elem = next(e for e in matching_form["elements"] if e["key"] == elem.element_key)
            assert elem.group_key == matching_elem["group_key"]
            
        # Verify element data is initialized (null is acceptable)
        for elem in elements:
            # data can be None or empty dict
            assert elem.data is None or elem.data == {}
