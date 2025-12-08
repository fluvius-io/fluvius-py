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


# Domain and setup_db fixtures are now in conftest.py
# setup_db runs once per session to preserve data for inspection


async def create_test_collection(domain):
    """Helper to create a test collection"""
    collection_id = UUID_GENR()
    async with domain.statemgr.transaction():
        collection = domain.statemgr.create(
            "collection",
            _id=collection_id,
            collection_key=f"test-collection-{str(collection_id)[:8]}",
            collection_name="Test Collection",
            desc="A test collection",
            organization_id=FIXTURE_ORGANIZATION_ID,
        )
        await domain.statemgr.insert(collection)
        return collection


async def create_test_template(domain, collection_id=None):
    """Helper to create a test template with all definitions"""
    template_id = UUID_GENR()
    
    async with domain.statemgr.transaction():
        # Create collection if not provided (required for template)
        if collection_id is None:
            collection_id = UUID_GENR()
            collection = domain.statemgr.create(
                "collection",
                _id=collection_id,
                collection_key=f"test-collection-{str(collection_id)[:8]}",
                collection_name="Test Collection for Template",
                organization_id=FIXTURE_ORGANIZATION_ID,
            )
            await domain.statemgr.insert(collection)
        
        template = domain.statemgr.create(
            "template",
            _id=template_id,
            template_key=f"test-template-{str(template_id)[:8]}",
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
        
        # Link form to template
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
        
        # Link element to form
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
        "template": template,
        "template_id": template_id,
        "collection_id": collection_id,
        "section_def_id": section_def_id,
        "section_key": section_key,
        "form_def_id": form_def_id,
        "form_key": form_key,
        "group_def_id": group_def_id,
        "element_def_id": element_def_id,
        "element_key": element_key,
    }


async def create_test_document(domain, template_id, collection_id=None):
    """Helper to create a test document"""
    document_id = UUID_GENR()
    async with domain.statemgr.transaction():
        document = domain.statemgr.create(
            "document",
            _id=document_id,
            template_id=template_id,
            document_key=f"test-document-{str(document_id)[:8]}",
            document_name="Test Document",
            desc="A test document",
            version=1,
            organization_id=FIXTURE_ORGANIZATION_ID,
            resource_id=UUID_GENR(),
            resource_name="test-resource",
        )
        await domain.statemgr.insert(document)
        
        # Add to collection if specified
        if collection_id:
            doc_collection = domain.statemgr.create(
                "document_collection",
                _id=UUID_GENR(),
                document_id=document_id,
                collection_id=collection_id,
                order=0,
            )
            await domain.statemgr.insert(doc_collection)
        
        return document


@mark.asyncio
async def test_query_collections(domain):
    """Test querying collections"""
    test_collection = await create_test_collection(domain)
    
    async with domain.statemgr.transaction():
        collections = await domain.statemgr.query('collection')
        assert len(collections) > 0
        found = False
        for collection in collections:
            if collection.collection_key == test_collection.collection_key:
                found = True
                assert collection.collection_name == "Test Collection"
                assert collection.organization_id == FIXTURE_ORGANIZATION_ID
        assert found


@mark.asyncio
async def test_query_templates(domain):
    """Test querying templates"""
    template_data = await create_test_template(domain)
    
    async with domain.statemgr.transaction():
        templates = await domain.statemgr.query('template')
        assert len(templates) > 0
        found = False
        for template in templates:
            if template.template_key == template_data["template"].template_key:
                found = True
                assert template.template_name == "Test Template"
                assert template.organization_id == FIXTURE_ORGANIZATION_ID
        assert found


@mark.asyncio
async def test_query_documents(domain):
    """Test querying documents"""
    template_data = await create_test_template(domain)
    test_document = await create_test_document(domain, template_data["template_id"])
    
    async with domain.statemgr.transaction():
        documents = await domain.statemgr.query('document')
        assert len(documents) > 0
        found = False
        for document in documents:
            if document.document_key == test_document.document_key:
                found = True
                assert document.document_name == "Test Document"
                assert document.organization_id == FIXTURE_ORGANIZATION_ID
                assert document.resource_name == "test-resource"
        assert found


@mark.asyncio
async def test_query_template_sections(domain):
    """Test querying section definitions"""
    template_data = await create_test_template(domain)
    
    async with domain.statemgr.transaction():
        section_defs = await domain.statemgr.query(
            'template_section',
            where={'template_id': template_data["template_id"]}
        )
        assert len(section_defs) > 0
        assert section_defs[0].template_id == template_data["template_id"]


@mark.asyncio
async def test_query_form_definitions(domain):
    """Test querying form definitions"""
    template_data = await create_test_template(domain)
    
    async with domain.statemgr.transaction():
        form_defs = await domain.statemgr.query('form_definition')
        assert len(form_defs) > 0
        found = any(fd._id == template_data["form_def_id"] for fd in form_defs)
        assert found


@mark.asyncio
async def test_query_form_element_groups(domain):
    """Test querying element group definitions"""
    template_data = await create_test_template(domain)
    
    async with domain.statemgr.transaction():
        group_defs = await domain.statemgr.query(
            'form_element_group',
            where={'form_definition_id': template_data["form_def_id"]}
        )
        assert len(group_defs) > 0
        assert group_defs[0].form_definition_id == template_data["form_def_id"]


@mark.asyncio
async def test_query_element_definitions(domain):
    """Test querying element definitions"""
    template_data = await create_test_template(domain)
    
    async with domain.statemgr.transaction():
        element_defs = await domain.statemgr.query('element_definition')
        assert len(element_defs) > 0
        found = any(ed._id == template_data["element_def_id"] for ed in element_defs)
        assert found


@mark.asyncio
async def test_query_document_by_resource(domain):
    """Test querying documents by resource_id"""
    template_data = await create_test_template(domain)
    test_document = await create_test_document(domain, template_data["template_id"])
    
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
    test_collection = await create_test_collection(domain)
    
    async with domain.statemgr.transaction():
        collections = await domain.statemgr.query(
            'collection',
            where={'organization_id': FIXTURE_ORGANIZATION_ID}
        )
        assert len(collections) > 0
        for collection in collections:
            assert collection.organization_id == FIXTURE_ORGANIZATION_ID


@mark.asyncio
async def test_query_documents_in_collection(domain):
    """Test querying documents within a collection"""
    collection = await create_test_collection(domain)
    template_data = await create_test_template(domain, collection._id)
    test_document = await create_test_document(domain, template_data["template_id"], collection._id)
    
    async with domain.statemgr.transaction():
        # Query document_collection junction table
        doc_collections = await domain.statemgr.query(
            'document_collection',
            where={'collection_id': collection._id}
        )
        assert len(doc_collections) > 0
        
        # Get document IDs
        document_ids = [dc.document_id for dc in doc_collections]
        assert test_document._id in document_ids


@mark.asyncio
async def test_query_templates_by_collection(domain):
    """Test querying templates by collection_id"""
    collection = await create_test_collection(domain)
    template_data = await create_test_template(domain, collection._id)
    
    async with domain.statemgr.transaction():
        # Templates have collection_id directly
        templates = await domain.statemgr.query(
            'template',
            where={'collection_id': collection._id}
        )
        assert len(templates) > 0
        assert templates[0].collection_id == collection._id
