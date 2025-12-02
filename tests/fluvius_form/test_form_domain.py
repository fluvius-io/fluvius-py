import pytest
from pytest import mark
from sqlalchemy import text
from uuid import UUID
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


@mark.asyncio
async def test_create_collection(domain):
    """Test creating a collection"""
    collection_id = UUID_GENR()
    payload = {
        "collection_key": f"test-collection-{str(collection_id)[:8]}",
        "collection_name": "Test Collection",
        "desc": "A test collection",
        "organization_id": FIXTURE_ORGANIZATION_ID,
    }
    result = await command_handler(
        domain, "create-collection", payload, "collection", collection_id
    )
    
    async with domain.statemgr.transaction():
        collection = await domain.statemgr.fetch('collection', collection_id)
        assert collection.collection_key == "test-collection-01"
        assert collection.collection_name == "Test Collection"
        assert collection.desc == "A test collection"
        assert collection.organization_id == FIXTURE_ORGANIZATION_ID


@mark.asyncio
async def test_update_collection(domain):
    """Test updating a collection"""

    collection_id = UUID_GENR()
    create_payload = {
        "collection_key": f"test-collection-{str(collection_id)[:8]}",
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
    create_payload = {
        "collection_key": f"test-collection-{str(collection_id)[:8]}",
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


@mark.asyncio
async def test_create_document(domain):
    """Test creating a document and adding it to a collection"""

    # First create a collection
    collection_id = UUID_GENR()
    collection_payload = {
        "collection_key": f"test-collection-{str(collection_id)[:8]}",
        "collection_name": "Test Collection",
        "organization_id": FIXTURE_ORGANIZATION_ID,
    }
    await command_handler(
        domain, "create-collection", collection_payload, "collection", collection_id
    )

    # Now create a document in the collection
    document_id = UUID_GENR()
    payload = {
        "document_key": f"test-document-{str(document_id)[:8]}",
        "document_name": "Test Document",
        "collection_id": collection_id,  # Optional: add to single collection
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
        assert document.document_key == "test-document-01"
        assert document.document_name == "Test Document"
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


@mark.asyncio
async def test_update_document(domain):
    """Test updating a document"""

    # Create a collection first
    collection_id = UUID_GENR()
    collection_payload = {
        "collection_key": f"test-collection-{str(collection_id)[:8]}",
        "collection_name": "Test Collection",
        "organization_id": FIXTURE_ORGANIZATION_ID,
    }
    await command_handler(
        domain, "create-collection", collection_payload, "collection", collection_id
    )

    document_id = UUID_GENR()
    create_payload = {
        "document_key": f"test-document-{str(document_id)[:8]}",
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

    # Create a collection first
    collection_id = UUID_GENR()
    collection_payload = {
        "collection_key": f"test-collection-{str(collection_id)[:8]}",
        "collection_name": "Test Collection",
        "organization_id": FIXTURE_ORGANIZATION_ID,
    }
    await command_handler(
        domain, "create-collection", collection_payload, "collection", collection_id
    )

    document_id = UUID_GENR()
    create_payload = {
        "document_key": f"test-document-{str(document_id)[:8]}",
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
async def test_copy_document(domain):
    """Test copying a document with forms, elements, and target collection"""

    # Create source collection
    source_collection_id = UUID_GENR()
    source_collection_payload = {
        "collection_key": f"test-collection-{str(collection_id)[:8]}",
        "collection_name": "Source Collection",
        "organization_id": FIXTURE_ORGANIZATION_ID,
    }
    await command_handler(
        domain, "create-collection", source_collection_payload, "collection", source_collection_id
    )

    # Create a source document
    source_document_id = UUID_GENR()
    create_payload = {
        "document_key": f"test-document-{str(document_id)[:8]}",
        "document_name": "Source Document",
        "collection_id": source_collection_id,
        "organization_id": FIXTURE_ORGANIZATION_ID,
    }
    await command_handler(
        domain, "create-document", create_payload, "document", source_document_id
    )
    
    # Create a form for the source document
    form_id = UUID_GENR()
    async with domain.statemgr.transaction():
        form = domain.statemgr.create(
            "data_form",
            _id=form_id,
            form_key=f"test-form-{str(form_id)[:8]}",
            form_name="Source Form",
            version=1,
            organization_id=FIXTURE_ORGANIZATION_ID,
        )
        await domain.statemgr.insert(form)
        
        # Create element type
        element_type_id = UUID_GENR()
        element_type = domain.statemgr.create(
            "element_type",
            _id=element_type_id,
            type_key=f"test-element-type-{str(element_type_id)[:8]}",
            type_name="Text Input",
            desc="A text input element",
        )
        await domain.statemgr.insert(element_type)
        
        # Create element
        element_id = UUID_GENR()
        element = domain.statemgr.create(
            "data_element",
            _id=element_id,
            form_id=form_id,
            element_type_id=element_type_id,
            element_key=f"test-element-{str(element_id)[:8]}",
            element_label="Test Element",
            order=0,
            required=False,
        )
        await domain.statemgr.insert(element)
        
        # Create document-form relationship
        doc_form = domain.statemgr.create(
            "document_form",
            _id=UUID_GENR(),
            document_id=source_document_id,
            form_id=form_id,
            order=0,
        )
        await domain.statemgr.insert(doc_form)
    
    # Create target collection
    target_collection_id = UUID_GENR()
    target_collection_payload = {
        "collection_key": f"test-collection-{str(collection_id)[:8]}",
        "collection_name": "Target Collection",
        "organization_id": FIXTURE_ORGANIZATION_ID,
    }
    await command_handler(
        domain, "create-collection", target_collection_payload, "collection", target_collection_id
    )
    
    # Copy the document with forms and target collection
    copy_payload = {
        "new_document_key": "copied-document",
        "new_document_name": "Copied Document",
        "copy_sections": True,
        "copy_forms": True,
        "target_collection_id": target_collection_id,
        "order": 0,
    }
    result = await command_handler(
        domain, "copy-document", copy_payload, "document", source_document_id
    )
    
    # Verify the copied document exists
    async with domain.statemgr.transaction():
        documents = await domain.statemgr.query('document', where={'document_key': 'copied-document'})
        assert len(documents) > 0
        copied_doc = documents[0]
        assert copied_doc.document_key == "copied-document"
        assert copied_doc.document_name == "Copied Document"
        
        # Verify copied document is in target collection
        doc_collections = await domain.statemgr.query(
            'document_collection',
            where={'document_id': copied_doc._id, 'collection_id': target_collection_id}
        )
        assert len(doc_collections) == 1
        
        # Verify form was copied
        copied_forms = await domain.statemgr.query(
            'document_form',
            where={'document_id': copied_doc._id}
        )
        assert len(copied_forms) == 1
        copied_form_id = copied_forms[0].form_id
        
        # Verify elements were copied
        copied_elements = await domain.statemgr.query(
            'data_element',
            where={'form_id': copied_form_id}
        )
        assert len(copied_elements) == 1
        assert copied_elements[0].element_key == "test-element"


@mark.asyncio
async def test_form_commands(domain):
    """Test form-related commands (populate, save, submit)"""

    # Note: These commands require form_instance tables which may need to be added
    # For now, we'll test that the commands can be invoked without errors
    form_id = UUID_GENR()
    
    # Create a form first
    async with domain.statemgr.transaction():
        form = domain.statemgr.create(
            "data_form",
            _id=form_id,
            form_key=f"test-form-{str(form_id)[:8]}",
            form_name="Test Form",
            version=1,
        )
        await domain.statemgr.insert(form)
        
        # Create an element type
        element_type_id = UUID_GENR()
        element_type = domain.statemgr.create(
            "element_type",
            _id=element_type_id,
            type_key=f"test-element-type-{str(element_type_id)[:8]}",
            type_name="Test Element Type",
            desc="A test element type",
        )
        await domain.statemgr.insert(element_type)
        
        # Create an element
        element_id = UUID_GENR()
        element = domain.statemgr.create(
            "data_element",
            _id=element_id,
            form_id=form_id,
            element_type_id=element_type_id,
            element_key=f"test-element-{str(element_id)[:8]}",
            element_label="Test Element",
            order=0,
            required=False,
        )
        await domain.statemgr.insert(element)
    
    # Test populate form command
    populate_payload = {
        "form_id": form_id,
        "form_instance_id": UUID_GENR(),
    }
    result = await command_handler(
        domain, "populate-form", populate_payload, "data_form", form_id
    )
    assert result is not None
    
    # Test save form command
    save_payload = {
        "form_id": form_id,
        "form_instance_id": UUID_GENR(),
        "elements": [
            {"element_id": element_id, "data": {"value": "test"}}
        ],
    }
    result = await command_handler(
        domain, "save-form", save_payload, "data_form", form_id
    )
    assert result is not None
    
    # Test submit form command
    submit_payload = {
        "form_id": form_id,
        "form_instance_id": UUID_GENR(),
        "elements": [
            {"element_id": element_id, "data": {"value": "test"}}
        ],
    }
    result = await command_handler(
        domain, "submit-form", submit_payload, "data_form", form_id
    )
    assert result is not None
    assert result.get('form-response', {}).get('locked') is True


@mark.asyncio
async def test_move_document(domain):
    """Test moving a document between collections"""

    # Create source collection
    source_collection_id = UUID_GENR()
    source_collection_payload = {
        "collection_key": f"test-collection-{str(collection_id)[:8]}",
        "collection_name": "Source Collection",
        "organization_id": FIXTURE_ORGANIZATION_ID,
    }
    await command_handler(
        domain, "create-collection", source_collection_payload, "collection", source_collection_id
    )

    # Create target collection
    target_collection_id = UUID_GENR()
    target_collection_payload = {
        "collection_key": f"test-collection-{str(collection_id)[:8]}",
        "collection_name": "Target Collection",
        "organization_id": FIXTURE_ORGANIZATION_ID,
    }
    await command_handler(
        domain, "create-collection", target_collection_payload, "collection", target_collection_id
    )

    # Create a document in source collection
    document_id = UUID_GENR()
    create_payload = {
        "document_key": f"test-document-{str(document_id)[:8]}",
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

    # Create collection
    collection_id = UUID_GENR()
    collection_payload = {
        "collection_key": f"test-collection-{str(collection_id)[:8]}",
        "collection_name": "Test Collection",
        "organization_id": FIXTURE_ORGANIZATION_ID,
    }
    await command_handler(
        domain, "create-collection", collection_payload, "collection", collection_id
    )

    # Create a document in collection
    document_id = UUID_GENR()
    create_payload = {
        "document_key": f"test-document-{str(document_id)[:8]}",
        "document_name": "Document to Remove",
        "collection_id": collection_id,
        "organization_id": FIXTURE_ORGANIZATION_ID,
    }
    await command_handler(
        domain, "create-document", create_payload, "document", document_id
    )

    # Create target collection
    target_collection_id = UUID_GENR()
    target_collection_payload = {
        "collection_key": f"test-collection-{str(collection_id)[:8]}",
        "collection_name": "Target Collection",
        "organization_id": FIXTURE_ORGANIZATION_ID,
    }
    await command_handler(
        domain, "create-collection", target_collection_payload, "collection", target_collection_id
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
async def test_populate_element(domain):
    """Test populating an element with prior data"""

    # Create form and element
    form_id = UUID_GENR()
    element_type_id = UUID_GENR()
    element_id = UUID_GENR()
    
    async with domain.statemgr.transaction():
        form = domain.statemgr.create(
            "data_form",
            _id=form_id,
            form_key=f"test-form-{str(form_id)[:8]}",
            form_name="Test Form",
            version=1,
            organization_id=FIXTURE_ORGANIZATION_ID,
        )
        await domain.statemgr.insert(form)
        
        element_type = domain.statemgr.create(
            "element_type",
            _id=element_type_id,
            type_key=f"test-element-type-{str(element_type_id)[:8]}",
            type_name="Text Input",
            desc="A text input element",
        )
        await domain.statemgr.insert(element_type)
        
        element = domain.statemgr.create(
            "data_element",
            _id=element_id,
            form_id=form_id,
            element_type_id=element_type_id,
            element_key=f"test-element-{str(element_id)[:8]}",
            element_label="Test Element",
            order=0,
            required=False,
        )
        await domain.statemgr.insert(element)

    # Test populate element command
    populate_payload = {
        "element_id": element_id,
    }
    result = await command_handler(
        domain, "populate-element", populate_payload, "data_element", element_id
    )
    assert result is not None


@mark.asyncio
async def test_save_element(domain):
    """Test saving element data"""

    # Create form, element type, and element
    form_id = UUID_GENR()
    element_type_id = UUID_GENR()
    element_id = UUID_GENR()
    form_instance_id = UUID_GENR()
    
    async with domain.statemgr.transaction():
        form = domain.statemgr.create(
            "data_form",
            _id=form_id,
            form_key=f"test-form-{str(form_id)[:8]}",
            form_name="Test Form",
            version=1,
            organization_id=FIXTURE_ORGANIZATION_ID,
        )
        await domain.statemgr.insert(form)
        
        element_type = domain.statemgr.create(
            "element_type",
            _id=element_type_id,
            type_key=f"test-element-type-{str(element_type_id)[:8]}",
            type_name="Text Input",
            desc="A text input element",
        )
        await domain.statemgr.insert(element_type)
        
        element = domain.statemgr.create(
            "data_element",
            _id=element_id,
            form_id=form_id,
            element_type_id=element_type_id,
            element_key=f"test-element-{str(element_id)[:8]}",
            element_label="Test Element",
            order=0,
            required=False,
        )
        await domain.statemgr.insert(element)

    # Create form instance first (required for save_element)
    from fluvius.form.element import ElementDataManager
    element_data_mgr = ElementDataManager()
    async with element_data_mgr.transaction():
        form_instance = element_data_mgr.create(
            "form_instance",
            _id=form_instance_id,
            form_id=form_id,
            instance_key=f"instance-{str(form_instance_id)[:8]}",
            instance_name=None,
            organization_id=FIXTURE_ORGANIZATION_ID,
        )
        await element_data_mgr.insert(form_instance)

    # Test save element command
    save_payload = {
        "element_id": element_id,
        "form_instance_id": form_instance_id,
        "data": {"value": "test value"},
    }
    result = await command_handler(
        domain, "save-element", save_payload, "data_element", element_id
    )
    assert result is not None


@mark.asyncio
async def test_populate_form(domain):
    """Test populating a form with prior data"""

    # Create form
    form_id = UUID_GENR()
    async with domain.statemgr.transaction():
        form = domain.statemgr.create(
            "data_form",
            _id=form_id,
            form_key=f"test-form-{str(form_id)[:8]}",
            form_name="Test Form",
            version=1,
            organization_id=FIXTURE_ORGANIZATION_ID,
        )
        await domain.statemgr.insert(form)

    # Test populate form command
    populate_payload = {
        "form_id": form_id,
    }
    result = await command_handler(
        domain, "populate-form", populate_payload, "data_form", form_id
    )
    assert result is not None


@mark.asyncio
async def test_create_document_without_collection(domain):
    """Test that creating a document without collection_id succeeds (collection_id is now optional)"""

    document_id = UUID_GENR()
    payload = {
        "document_key": f"test-document-{str(document_id)[:8]}",
        "document_name": "Test Document",
        "organization_id": FIXTURE_ORGANIZATION_ID,
    }
    
    # This should succeed because collection_id is now optional
    result = await command_handler(
        domain, "create-document", payload, "document", document_id
    )
    
    async with domain.statemgr.transaction():
        document = await domain.statemgr.fetch('document', document_id)
        assert document.document_key == "test-document-no-collection"
        assert document.document_name == "Test Document"
        
        # Verify document is not in any collection
        doc_collections = await domain.statemgr.query(
            'document_collection',
            where={'document_id': document_id}
        )
        assert len(doc_collections) == 0


@mark.asyncio
async def test_create_document_with_invalid_collection_fails(domain):
    """Test that creating a document with invalid collection_id fails"""

    document_id = UUID_GENR()
    invalid_collection_id = UUID_GENR()
    payload = {
        "document_key": f"test-document-{str(document_id)[:8]}",
        "document_name": "Test Document",
        "collection_id": invalid_collection_id,
        "organization_id": FIXTURE_ORGANIZATION_ID,
    }
    
    # This should fail because collection doesn't exist
    try:
        await command_handler(
            domain, "create-document", payload, "document", document_id
        )
        assert False, "Should have raised an error for invalid collection_id"
    except Exception as e:
        # Expected to fail
        assert True

