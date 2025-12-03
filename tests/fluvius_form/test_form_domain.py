import pytest
from pytest import mark
from sqlalchemy import text
from uuid import UUID
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


async def create_test_template(domain, collection_id=None):
    """Helper to create a test template with section, form, element group, and element definitions"""
    template_id = UUID_GENR()
    template_key = f"test-template-{str(template_id)[:8]}"
    
    # Create template
    async with domain.statemgr.transaction():
        template = domain.statemgr.create(
            "template",
            _id=template_id,
            template_key=template_key,
            template_name="Test Template",
            desc="A test template",
            version=1,
            organization_id=FIXTURE_ORGANIZATION_ID,
        )
        await domain.statemgr.insert(template)
        
        # Add to collection if specified
        if collection_id:
            template_collection = domain.statemgr.create(
                "template_collection",
                _id=UUID_GENR(),
                template_id=template_id,
                collection_id=collection_id,
                order=0,
            )
            await domain.statemgr.insert(template_collection)
        
        # Create section definition
        section_def_id = UUID_GENR()
        section_def = domain.statemgr.create(
            "section_definition",
            _id=section_def_id,
            template_id=template_id,
            section_key=f"section-{str(section_def_id)[:8]}",
            section_name="Test Section",
            desc="A test section",
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
            desc="A test form",
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
            desc="A test element group",
            order=0,
        )
        await domain.statemgr.insert(group_def)
        
        # Create element type
        element_type_id = UUID_GENR()
        element_type = domain.statemgr.create(
            "element_type",
            _id=element_type_id,
            type_key=f"text-input-{str(element_type_id)[:8]}",
            type_name="Text Input",
            desc="A text input element",
        )
        await domain.statemgr.insert(element_type)
        
        # Create element definition
        element_def_id = UUID_GENR()
        element_def = domain.statemgr.create(
            "element_definition",
            _id=element_def_id,
            element_group_definition_id=group_def_id,
            element_type_id=element_type_id,
            element_key=f"element-{str(element_def_id)[:8]}",
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
        "element_def_id": element_def_id,
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
        section_instances = await domain.statemgr.query(
            'section_instance',
            where={'document_id': document_id}
        )
        assert len(section_instances) >= 1


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
# ELEMENT TYPE TESTS
# ============================================================================

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


# ============================================================================
# SECTION DEFINITION TESTS
# ============================================================================

@mark.asyncio
async def test_section_definition_creation(domain):
    """Test creating section definitions within a template"""
    template_id = UUID_GENR()
    template_key = f"test-template-{str(template_id)[:8]}"
    
    async with domain.statemgr.transaction():
        template = domain.statemgr.create(
            "template",
            _id=template_id,
            template_key=template_key,
            template_name="Test Template",
            version=1,
            organization_id=FIXTURE_ORGANIZATION_ID,
        )
        await domain.statemgr.insert(template)
        
        section_def_id = UUID_GENR()
        section_key = f"section-{str(section_def_id)[:8]}"
        section_def = domain.statemgr.create(
            "section_definition",
            _id=section_def_id,
            template_id=template_id,
            section_key=section_key,
            section_name="Test Section",
            desc="A test section definition",
            order=0,
        )
        await domain.statemgr.insert(section_def)
        
        fetched = await domain.statemgr.fetch('section_definition', section_def_id)
        assert fetched.section_key == section_key
        assert fetched.section_name == "Test Section"
        assert fetched.template_id == template_id


# ============================================================================
# FORM DEFINITION TESTS
# ============================================================================

@mark.asyncio
async def test_form_definition_creation(domain):
    """Test creating form definitions within a section definition"""
    template_data = await create_test_template(domain)
    
    async with domain.statemgr.transaction():
        form_def_id = UUID_GENR()
        form_key = f"form-{str(form_def_id)[:8]}"
        form_def = domain.statemgr.create(
            "form_definition",
            _id=form_def_id,
            section_definition_id=template_data["section_def_id"],
            form_key=form_key,
            title="Another Test Form",
            desc="Another test form definition",
            order=1,
        )
        await domain.statemgr.insert(form_def)
        
        fetched = await domain.statemgr.fetch('form_definition', form_def_id)
        assert fetched.form_key == form_key
        assert fetched.title == "Another Test Form"
        assert fetched.section_definition_id == template_data["section_def_id"]


# ============================================================================
# ELEMENT GROUP DEFINITION TESTS
# ============================================================================

@mark.asyncio
async def test_element_group_definition_creation(domain):
    """Test creating element group definitions within a form definition"""
    template_data = await create_test_template(domain)
    
    async with domain.statemgr.transaction():
        group_def_id = UUID_GENR()
        group_key = f"group-{str(group_def_id)[:8]}"
        group_def = domain.statemgr.create(
            "element_group_definition",
            _id=group_def_id,
            form_definition_id=template_data["form_def_id"],
            group_key=group_key,
            group_name="Another Group",
            desc="Another test group",
            order=1,
        )
        await domain.statemgr.insert(group_def)
        
        fetched = await domain.statemgr.fetch('element_group_definition', group_def_id)
        assert fetched.group_key == group_key
        assert fetched.group_name == "Another Group"
        assert fetched.form_definition_id == template_data["form_def_id"]


# ============================================================================
# ELEMENT DEFINITION TESTS
# ============================================================================

@mark.asyncio
async def test_element_definition_creation(domain):
    """Test creating element definitions within an element group definition"""
    template_data = await create_test_template(domain)
    
    async with domain.statemgr.transaction():
        element_def_id = UUID_GENR()
        element_key = f"element-{str(element_def_id)[:8]}"
        element_def = domain.statemgr.create(
            "element_definition",
            _id=element_def_id,
            element_group_definition_id=template_data["group_def_id"],
            element_type_id=template_data["element_type_id"],
            element_key=element_key,
            element_label="Another Element",
            order=1,
            required=True,
        )
        await domain.statemgr.insert(element_def)
        
        fetched = await domain.statemgr.fetch('element_definition', element_def_id)
        assert fetched.element_key == element_key
        assert fetched.element_label == "Another Element"
        assert fetched.element_group_definition_id == template_data["group_def_id"]
        assert fetched.element_type_id == template_data["element_type_id"]
        assert fetched.required is True


@mark.asyncio
async def test_element_definition_with_resource_fields(domain):
    """Test that element definitions can have resource_name and resource_id fields"""
    template_data = await create_test_template(domain)
    resource_id = UUID_GENR()
    
    async with domain.statemgr.transaction():
        element_def_id = UUID_GENR()
        element_key = f"element-{str(element_def_id)[:8]}"
        element_def = domain.statemgr.create(
            "element_definition",
            _id=element_def_id,
            element_group_definition_id=template_data["group_def_id"],
            element_type_id=template_data["element_type_id"],
            element_key=element_key,
            element_label="Element with Resource",
            order=2,
            required=False,
            resource_id=resource_id,
            resource_name="test-resource",
        )
        await domain.statemgr.insert(element_def)
        
        fetched = await domain.statemgr.fetch('element_definition', element_def_id)
        assert fetched.resource_id == resource_id
        assert fetched.resource_name == "test-resource"
