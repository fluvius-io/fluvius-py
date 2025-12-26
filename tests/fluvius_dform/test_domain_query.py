import pytest
from pytest import mark
from fluvius.data import UUID_GENR
from fluvius.auth import AuthorizationContext
from fluvius.query.model import FrontendQuery
from fluvius.dform.domain.query import FormQueryManager
from types import SimpleNamespace

FIXTURE_ORGANIZATION_ID = "05e8bb7e-43e6-4766-98d9-8f8c779dbe45"
FIXTURE_USER_ID = UUID_GENR()
FIXTURE_PROFILE_ID = UUID_GENR()

@pytest.fixture
def auth_ctx():
    # Use construct to bypass strict validation of Keycloak fields
    return AuthorizationContext.construct(
        user=SimpleNamespace(_id=FIXTURE_USER_ID, id=FIXTURE_USER_ID, sub=FIXTURE_USER_ID, username="testuser"),
        profile=SimpleNamespace(_id=FIXTURE_PROFILE_ID, id=FIXTURE_PROFILE_ID, display_name="Test User", roles=["admin"]),
        organization=SimpleNamespace(_id=FIXTURE_ORGANIZATION_ID, id=FIXTURE_ORGANIZATION_ID, name="Test Org"),
        realm="test",
        iamroles=["admin"]
    )

@mark.asyncio
async def test_query_resources(domain, auth_ctx):
    """Test standard queries for all registered resources using FormQueryManager"""
    
    # Inline setup to ensure data is committed
    async with domain.statemgr.transaction():
        # 1. Collection
        collection_id = UUID_GENR()
        collection = domain.statemgr.create(
            "collection",
            _id=collection_id,
            collection_key=f"col-{str(collection_id)[:8]}",
            collection_name="Query Test Collection",
            organization_id=FIXTURE_ORGANIZATION_ID
        )
        await domain.statemgr.insert(collection)
        
        # 2. Template
        template_id = UUID_GENR()
        template = domain.statemgr.create(
            "template_registry",
            _id=template_id,
            template_key=f"tpl-{str(template_id)[:8]}",
            template_name="Query Test Template",
            collection_id=collection_id,
            organization_id=FIXTURE_ORGANIZATION_ID
        )
        await domain.statemgr.insert(template)
        
        # 3. Form Registry
        form_id = UUID_GENR()
        form_def = domain.statemgr.create(
            "form_registry",
            _id=form_id,
            form_key=f"form-{str(form_id)[:8]}",
            title="Query Test Form",
            desc="Description for query test"
        )
        await domain.statemgr.insert(form_def)
        
        # 4. Element Registry
        element_id = UUID_GENR()
        element_def = domain.statemgr.create(
            "element_registry",
            _id=element_id,
            element_key=f"elem-{str(element_id)[:8]}",
            element_label="Query Test Element",
            element_schema={"type": "text"}
        )
        await domain.statemgr.insert(element_def)
        
        # 5. Document
        doc_id = UUID_GENR()
        doc = domain.statemgr.create(
            "document",
            _id=doc_id,
            template_id=template_id,
            document_key=f"doc-{str(doc_id)[:8]}",
            document_name="Query Test Document",
            organization_id=FIXTURE_ORGANIZATION_ID
        )
        await domain.statemgr.insert(doc)
        
        # 6. Document Node
        node_id = UUID_GENR()
        node = domain.statemgr.create(
            "document_node",
            _id=node_id,
            document_id=doc_id,
            node_key="section-1",
            title="Main Section",
            node_type="section"
        )
        await domain.statemgr.insert(node)
        
        # 7. Form Submission
        sub_id = UUID_GENR()
        submission = domain.statemgr.create(
            "form_submission",
            _id=sub_id,
            document_id=doc_id,
            form_key=form_def.form_key,
            title="My Submission",
            status="draft"
        )
        await domain.statemgr.insert(submission)
        
        # 8. Form Element (Data Instance)
        field_id = UUID_GENR()
        field = domain.statemgr.create(
            "form_element",
            _id=field_id,
            form_submission_id=sub_id,
            element_registry_id=element_id,
            element_name="field_1",
            data={"value": "test data"}
        )
        await domain.statemgr.insert(field)

    # Initialize Query Manager
    # Note: mocking policymgr to simple pass-through if needed, but QueryManager checks config.QUERY_PERMISSION
    qm = FormQueryManager(app=None)
    
    # --- Tests via FormQueryManager ---
    
    # 1. Collection
    fe_query = FrontendQuery(user_query={'id': str(collection_id)})
    res, _ = await qm.query_resource(auth_ctx, 'collection', fe_query)
    assert len(res) == 1
    assert res[0].collection_name == "Query Test Collection"

    # 2. Template (This was failing before)
    fe_query = FrontendQuery(user_query={'id': str(template_id)})
    res, _ = await qm.query_resource(auth_ctx, 'template', fe_query)
    assert len(res) == 1
    assert res[0].template_name == "Query Test Template"

    # 3. Form Registry
    fe_query = FrontendQuery(user_query={'form_key': form_def.form_key})
    res, _ = await qm.query_resource(auth_ctx, 'form-registry', fe_query)
    assert len(res) == 1
    assert res[0].title == "Query Test Form"

    # 4. Element Registry
    fe_query = FrontendQuery(user_query={'element_key': element_def.element_key})
    res, _ = await qm.query_resource(auth_ctx, 'element-registry', fe_query)
    assert len(res) == 1
    assert res[0].element_label == "Query Test Element"

    # 5. Document
    fe_query = FrontendQuery(user_query={'document_key': doc.document_key})
    res, _ = await qm.query_resource(auth_ctx, 'document', fe_query)
    assert len(res) == 1
    assert res[0].document_name == "Query Test Document"

    # 6. Document Node
    fe_query = FrontendQuery(user_query={'document_id': str(doc_id)})
    res, _ = await qm.query_resource(auth_ctx, 'document-node', fe_query)
    assert len(res) >= 1
    match = next((n for n in res if n.node_key == "section-1"), None)
    assert match is not None
    assert match.title == "Main Section"
    
    # 7. Form Submission
    fe_query = FrontendQuery(user_query={'document_id': str(doc_id)})
    res, _ = await qm.query_resource(auth_ctx, 'form-submission', fe_query)
    assert len(res) >= 1
    assert res[0].title == "My Submission"
    
    # 8. Form Element
    fe_query = FrontendQuery(user_query={'form_submission_id': str(sub_id)})
    res, _ = await qm.query_resource(auth_ctx, 'form-element', fe_query)
    assert len(res) >= 1
    assert res[0].element_name == "field_1"
    assert res[0].data['value'] == "test data"
