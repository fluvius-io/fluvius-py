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


@pytest.fixture
def domain():
    return FormDomain(None)


async def setup_db(domain):
    """Helper to setup database schema"""
    db = domain.statemgr.connector.engine
    async with db.begin() as conn:
        await conn.run_sync(FormConnector.__data_schema_base__.metadata.drop_all)
        await conn.run_sync(FormConnector.__data_schema_base__.metadata.create_all)


async def create_test_collection(domain):
    """Helper to create a test collection"""
    collection_id = UUID_GENR()
    async with domain.statemgr.transaction():
        collection = domain.statemgr.create(
            "collection",
            _id=collection_id,
            collection_key="test-collection",
            collection_name="Test Collection",
            desc="A test collection",
            organization_id=FIXTURE_ORGANIZATION_ID,
        )
        await domain.statemgr.insert(collection)
        return collection


async def create_test_document(domain):
    """Helper to create a test document"""
    document_id = UUID_GENR()
    async with domain.statemgr.transaction():
        document = domain.statemgr.create(
            "document",
            _id=document_id,
            document_key="test-document",
            document_name="Test Document",
            desc="A test document",
            version=1,
            organization_id=FIXTURE_ORGANIZATION_ID,
            resource_id=UUID_GENR(),
            resource_name="test-resource",
        )
        await domain.statemgr.insert(document)
        return document


async def create_test_form(domain):
    """Helper to create a test form"""
    form_id = UUID_GENR()
    async with domain.statemgr.transaction():
        form = domain.statemgr.create(
            "data_form",
            _id=form_id,
            form_key="test-form",
            form_name="Test Form",
            desc="A test form",
            version=1,
            organization_id=FIXTURE_ORGANIZATION_ID,
        )
        await domain.statemgr.insert(form)
        return form


@mark.asyncio
async def test_query_collections(domain):
    """Test querying collections"""
    await setup_db(domain)
    test_collection = await create_test_collection(domain)
    
    async with domain.statemgr.transaction():
        collections = await domain.statemgr.query('collection')
        assert len(collections) > 0
        found = False
        for collection in collections:
            if collection.collection_key == "test-collection":
                found = True
                assert collection.collection_name == "Test Collection"
                assert collection.organization_id == FIXTURE_ORGANIZATION_ID
        assert found


@mark.asyncio
async def test_query_documents(domain):
    """Test querying documents"""
    await setup_db(domain)
    test_document = await create_test_document(domain)
    
    async with domain.statemgr.transaction():
        documents = await domain.statemgr.query('document')
        assert len(documents) > 0
        found = False
        for document in documents:
            if document.document_key == "test-document":
                found = True
                assert document.document_name == "Test Document"
                assert document.organization_id == FIXTURE_ORGANIZATION_ID
                assert document.resource_name == "test-resource"
        assert found


@mark.asyncio
async def test_query_forms(domain):
    """Test querying forms"""
    await setup_db(domain)
    test_form = await create_test_form(domain)
    
    async with domain.statemgr.transaction():
        forms = await domain.statemgr.query('data_form')
        assert len(forms) > 0
        found = False
        for form in forms:
            if form.form_key == "test-form":
                found = True
                assert form.form_name == "Test Form"
                assert form.organization_id == FIXTURE_ORGANIZATION_ID
        assert found


@mark.asyncio
async def test_query_document_by_resource(domain):
    """Test querying documents by resource_id"""
    await setup_db(domain)
    test_document = await create_test_document(domain)
    
    async with domain.statemgr.transaction():
        # Get the resource_id from the test document
        document = await domain.statemgr.fetch('document', test_document._id)
        resource_id = document.resource_id
        
        # Query by resource_id
        documents = await domain.statemgr.query('document', where={'resource_id': resource_id})
        assert len(documents) > 0
        assert documents[0].resource_id == resource_id


@mark.asyncio
async def test_query_collection_by_organization(domain):
    """Test querying collections by organization_id"""
    await setup_db(domain)
    test_collection = await create_test_collection(domain)
    
    async with domain.statemgr.transaction():
        collections = await domain.statemgr.query(
            'collection',
            where={'organization_id': FIXTURE_ORGANIZATION_ID}
        )
        assert len(collections) > 0
        for collection in collections:
            assert collection.organization_id == FIXTURE_ORGANIZATION_ID

