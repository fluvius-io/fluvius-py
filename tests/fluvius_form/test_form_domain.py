import pytest
from pytest import mark
from sqlalchemy import text
from fluvius.form.domain import FormDomain
from fluvius.form.model import FormConnector
from fluvius.data import UUID_GENR
from fluvius.domain.context import DomainTransport


FIXTURE_REALM = "fluvius-form-testing"
FIXTURE_USER_ID = UUID_GENR()
FIXTURE_ORGANIZATION_ID = "05e8bb7e-43e6-4766-98d9-8f8c779dbe45"
FIXTURE_PROFILE_ID = UUID_GENR()


async def command_handler(domain, cmd_key, payload, resource, identifier, scope={}, context={}):
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


@pytest.fixture
def domain():
    return FormDomain(None)


@pytest.fixture(autouse=True)
async def setup_database(domain):
    """Setup and teardown database for each test"""
    db = domain.statemgr.connector.engine
    async with db.begin() as conn:
        await conn.run_sync(FormConnector.__data_schema_base__.metadata.drop_all)
        await conn.run_sync(FormConnector.__data_schema_base__.metadata.create_all)
    yield
    async with db.begin() as conn:
        await conn.run_sync(FormConnector.__data_schema_base__.metadata.drop_all)


@mark.asyncio
async def test_create_collection(domain):
    """Test creating a collection"""
    collection_id = UUID_GENR()
    payload = {
        "collection_key": "test-collection-01",
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
        "collection_key": "test-collection-02",
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
        "collection_key": "test-collection-03",
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
    """Test creating a document"""
    document_id = UUID_GENR()
    payload = {
        "document_key": "test-document-01",
        "document_name": "Test Document",
        "desc": "A test document",
        "version": 1,
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


@mark.asyncio
async def test_update_document(domain):
    """Test updating a document"""
    document_id = UUID_GENR()
    create_payload = {
        "document_key": "test-document-02",
        "document_name": "Test Document",
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
    document_id = UUID_GENR()
    create_payload = {
        "document_key": "test-document-03",
        "document_name": "Test Document",
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
    """Test copying a document"""
    # First create a source document
    source_document_id = UUID_GENR()
    create_payload = {
        "document_key": "source-document",
        "document_name": "Source Document",
        "organization_id": FIXTURE_ORGANIZATION_ID,
    }
    await command_handler(
        domain, "create-document", create_payload, "document", source_document_id
    )
    
    # Create a section for the source document
    section_id = UUID_GENR()
    async with domain.statemgr.transaction():
        section = domain.statemgr.init_resource(
            "section",
            document_id=source_document_id,
            section_key="section-01",
            section_name="Section 01",
            order=0,
        )
        await domain.statemgr.save(section)
        section_id = section._id
    
    # Copy the document
    copy_payload = {
        "new_document_key": "copied-document",
        "new_document_name": "Copied Document",
        "copy_sections": True,
        "copy_forms": False,
    }
    result = await command_handler(
        domain, "copy-document", copy_payload, "document", source_document_id
    )
    
    # Verify the copied document exists
    async with domain.statemgr.transaction():
        # Find the copied document by document_key
        documents = await domain.statemgr.query('document', document_key='copied-document')
        assert len(documents) > 0
        copied_doc = documents[0]
        assert copied_doc.document_key == "copied-document"
        assert copied_doc.document_name == "Copied Document"


@mark.asyncio
async def test_form_commands(domain):
    """Test form-related commands (populate, save, submit)"""
    # Note: These commands require form_instance tables which may need to be added
    # For now, we'll test that the commands can be invoked without errors
    form_id = UUID_GENR()
    
    # Create a form first
    async with domain.statemgr.transaction():
        form = domain.statemgr.init_resource(
            "data_form",
            form_key="test-form-01",
            form_name="Test Form",
            version=1,
        )
        await domain.statemgr.save(form)
        form_id = form._id
    
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
            {"element_id": UUID_GENR(), "data": {"value": "test"}}
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
            {"element_id": UUID_GENR(), "data": {"value": "test"}}
        ],
    }
    result = await command_handler(
        domain, "submit-form", submit_payload, "data_form", form_id
    )
    assert result is not None
    assert result.get('form-response', {}).get('locked') is True

