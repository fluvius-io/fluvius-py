"""Tests for form submission commands: InitializeForm, UpdateForm, RemoveForm, SubmitForm."""
import pytest
from pytest import mark
from uuid import UUID
from fluvius.dform import FormDomain, logger
from fluvius.dform.schema import FormConnector
from fluvius.data import UUID_GENR
from fluvius.domain.context import DomainTransport
from fluvius.error import NotFoundError, BadRequestError


FIXTURE_REALM = "fluvius-form-testing"
FIXTURE_USER_ID = UUID_GENR()
FIXTURE_ORGANIZATION_ID = "05e8bb7e-43e6-4766-98d9-8f8c779dbe45"
FIXTURE_PROFILE_ID = UUID_GENR()


async def command_handler(domain, cmd_key, payload, resource, identifier, scope=None, context=None):
    """Helper to execute domain commands."""
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


async def create_test_form_registry(domain, suffix=None):
    """Helper to create a form registry entry and related element registries."""
    # Use unique suffix for each test to avoid conflicts
    suffix = suffix or str(UUID_GENR())[:8]
    form_registry_id = UUID_GENR()
    form_key = f"test-form-{suffix}"
    
    async with domain.statemgr.transaction():
        # Create form registry entry
        form_registry = domain.statemgr.create(
            "form_registry",
            _id=form_registry_id,
            form_key=form_key,
            title="Test Form",
            desc="A test form for form commands",
        )
        await domain.statemgr.insert(form_registry)
        
        # Create element registry entries with unique keys
        element1_id = UUID_GENR()
        element1 = domain.statemgr.create(
            "element_registry",
            _id=element1_id,
            element_key=f"first_name_{suffix}",
            element_label="First Name",
            element_schema={"type": "text", "placeholder": "Enter first name"},
        )
        await domain.statemgr.insert(element1)
        
        element2_id = UUID_GENR()
        element2 = domain.statemgr.create(
            "element_registry",
            _id=element2_id,
            element_key=f"last_name_{suffix}",
            element_label="Last Name",
            element_schema={"type": "text", "placeholder": "Enter last name"},
        )
        await domain.statemgr.insert(element2)
        
        element3_id = UUID_GENR()
        element3 = domain.statemgr.create(
            "element_registry",
            _id=element3_id,
            element_key=f"email_{suffix}",
            element_label="Email",
            element_schema={"type": "email", "placeholder": "Enter email"},
        )
        await domain.statemgr.insert(element3)
    
    return {
        "form_registry_id": form_registry_id,
        "form_key": form_key,
        "element_keys": [f"first_name_{suffix}", f"last_name_{suffix}", f"email_{suffix}"],
        "suffix": suffix,
    }


async def create_test_document(domain, template_id=None):
    """Helper to create a test document with template and collection."""
    document_id = UUID_GENR()
    document_key = f"test-doc-{str(document_id)[:8]}"
    
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
        
        # Create template registry if not provided (requires collection_id)
        if template_id is None:
            template_id = UUID_GENR()
            template = domain.statemgr.create(
                "template_registry",
                _id=template_id,
                template_key=f"test-template-{str(template_id)[:8]}",
                template_name="Test Template",
                desc="A test template",
                version=1,
                collection_id=collection_id,
            )
            await domain.statemgr.insert(template)
        
        # Create document
        document = domain.statemgr.create(
            "document",
            _id=document_id,
            template_id=template_id,
            document_key=document_key,
            document_name="Test Document",
            desc="A test document for form commands",
            version=1,
            organization_id=FIXTURE_ORGANIZATION_ID,
        )
        await domain.statemgr.insert(document)
    
    return {
        "document_id": document_id,
        "document_key": document_key,
        "template_id": template_id,
        "collection_id": collection_id,
    }


# ============================================================================
# INITIALIZE FORM TESTS
# ============================================================================

@mark.asyncio
async def test_initialize_form_basic(domain):
    """Test basic form initialization."""
    form_reg = await create_test_form_registry(domain)
    doc = await create_test_document(domain)
    
    payload = {
        "form_registry_id": form_reg["form_registry_id"],
        "form_key": "contact-form",
        "title": "Contact Information Form",
        "desc": "Fill in your contact details",
    }
    
    result = await command_handler(
        domain, "initialize-form", payload, "document", doc["document_id"]
    )
    
    async with domain.statemgr.transaction():
        form = await domain.statemgr.query(
            "form_submission",
            where={"document_id": doc["document_id"], "form_key": "contact-form"},
            limit=1
        )
        assert len(form) == 1
        assert form[0].title == "Contact Information Form"
        assert form[0].status == "draft"
        assert form[0].locked is False


@mark.asyncio
async def test_initialize_form_with_initial_data(domain):
    """Test form initialization with initial data."""
    form_reg = await create_test_form_registry(domain)
    doc = await create_test_document(domain)
    
    suffix = form_reg["suffix"]
    payload = {
        "form_registry_id": form_reg["form_registry_id"],
        "form_key": "prefilled-form",
        "title": "Pre-filled Form",
        "initial_data": {
            f"first_name_{suffix}": {"value": "John"},
            f"last_name_{suffix}": {"value": "Doe"},
        },
    }
    
    result = await command_handler(
        domain, "initialize-form", payload, "document", doc["document_id"]
    )
    
    async with domain.statemgr.transaction():
        forms = await domain.statemgr.query(
            "form_submission",
            where={"document_id": doc["document_id"], "form_key": "prefilled-form"},
            limit=1
        )
        assert len(forms) == 1
        
        elements = await domain.statemgr.query(
            "form_element",
            where={"form_submission_id": forms[0]._id}
        )
        element_names = {e.element_name for e in elements}
        assert f"first_name_{suffix}" in element_names
        assert f"last_name_{suffix}" in element_names


@mark.asyncio
async def test_initialize_form_duplicate_key_fails(domain):
    """Test that initializing a form with duplicate key fails."""
    form_reg = await create_test_form_registry(domain)
    doc = await create_test_document(domain)
    
    payload = {
        "form_registry_id": form_reg["form_registry_id"],
        "form_key": "unique-form",
        "title": "First Form",
    }
    
    await command_handler(
        domain, "initialize-form", payload, "document", doc["document_id"]
    )
    
    payload2 = {
        "form_registry_id": form_reg["form_registry_id"],
        "form_key": "unique-form",
        "title": "Second Form",
    }
    
    with pytest.raises(BadRequestError) as exc_info:
        await command_handler(
            domain, "initialize-form", payload2, "document", doc["document_id"]
        )
    
    assert "already exists" in str(exc_info.value)


# ============================================================================
# UPDATE FORM TESTS
# ============================================================================

@mark.asyncio
async def test_update_form_basic(domain):
    """Test basic form update."""
    form_reg = await create_test_form_registry(domain)
    doc = await create_test_document(domain)
    
    payload = {
        "form_registry_id": form_reg["form_registry_id"],
        "form_key": "update-test-form",
        "title": "Original Title",
    }
    
    await command_handler(
        domain, "initialize-form", payload, "document", doc["document_id"]
    )
    
    async with domain.statemgr.transaction():
        forms = await domain.statemgr.query(
            "form_submission",
            where={"document_id": doc["document_id"], "form_key": "update-test-form"},
            limit=1
        )
        form_id = forms[0]._id
    
    update_payload = {
        "title": "Updated Title",
        "desc": "Updated description",
    }
    
    result = await command_handler(
        domain, "update-form", update_payload, "form_submission", form_id
    )
    
    async with domain.statemgr.transaction():
        form = await domain.statemgr.fetch("form_submission", form_id)
        assert form.title == "Updated Title"
        assert form.desc == "Updated description"


@mark.asyncio
async def test_update_form_status(domain):
    """Test updating form status."""
    form_reg = await create_test_form_registry(domain)
    doc = await create_test_document(domain)
    
    payload = {
        "form_registry_id": form_reg["form_registry_id"],
        "form_key": "status-test-form",
        "title": "Status Test",
    }
    
    await command_handler(
        domain, "initialize-form", payload, "document", doc["document_id"]
    )
    
    async with domain.statemgr.transaction():
        forms = await domain.statemgr.query(
            "form_submission",
            where={"document_id": doc["document_id"], "form_key": "status-test-form"},
            limit=1
        )
        form_id = forms[0]._id
        assert forms[0].status == "draft"
    
    update_payload = {"status": "in_progress"}
    
    await command_handler(
        domain, "update-form", update_payload, "form_submission", form_id
    )
    
    async with domain.statemgr.transaction():
        form = await domain.statemgr.fetch("form_submission", form_id)
        assert form.status == "in_progress"


# ============================================================================
# REMOVE FORM TESTS
# ============================================================================

@mark.asyncio
async def test_remove_form(domain):
    """Test removing a form."""
    form_reg = await create_test_form_registry(domain)
    doc = await create_test_document(domain)
    
    payload = {
        "form_registry_id": form_reg["form_registry_id"],
        "form_key": "remove-test-form",
        "title": "Form to Remove",
    }
    
    await command_handler(
        domain, "initialize-form", payload, "document", doc["document_id"]
    )
    
    async with domain.statemgr.transaction():
        forms = await domain.statemgr.query(
            "form_submission",
            where={"document_id": doc["document_id"], "form_key": "remove-test-form"},
            limit=1
        )
        form_id = forms[0]._id
    
    result = await command_handler(
        domain, "remove-form", {}, "form_submission", form_id
    )
    
    async with domain.statemgr.transaction():
        form = await domain.statemgr.exist("form_submission", identifier=form_id)
        assert form is None


# ============================================================================
# SUBMIT FORM TESTS
# ============================================================================

@mark.asyncio
async def test_submit_form_basic(domain):
    """Test basic form submission with element data."""
    form_reg = await create_test_form_registry(domain)
    doc = await create_test_document(domain)
    suffix = form_reg["suffix"]
    
    init_payload = {
        "form_registry_id": form_reg["form_registry_id"],
        "form_key": "submit-test-form",
        "title": "Submit Test Form",
    }
    
    await command_handler(
        domain, "initialize-form", init_payload, "document", doc["document_id"]
    )
    
    async with domain.statemgr.transaction():
        forms = await domain.statemgr.query(
            "form_submission",
            where={"document_id": doc["document_id"], "form_key": "submit-test-form"},
            limit=1
        )
        form_id = forms[0]._id
    
    submit_payload = {
        "payload": {
            f"first_name_{suffix}": {"value": "Alice"},
            f"last_name_{suffix}": {"value": "Smith"},
            f"email_{suffix}": {"value": "alice@example.com"},
        },
        "status": "submitted",
    }
    
    result = await command_handler(
        domain, "submit-form", submit_payload, "form_submission", form_id
    )
    
    async with domain.statemgr.transaction():
        form = await domain.statemgr.fetch("form_submission", form_id)
        assert form.status == "submitted"
        assert form.locked is True
        
        elements = await domain.statemgr.query(
            "form_element",
            where={"form_submission_id": form_id}
        )
        # Verify elements were created
        assert len(elements) == 3
        element_names = {e.element_name for e in elements}
        assert f"first_name_{suffix}" in element_names
        assert f"last_name_{suffix}" in element_names
        assert f"email_{suffix}" in element_names


@mark.asyncio
async def test_submit_form_as_draft(domain):
    """Test saving form as draft (not submitting)."""
    form_reg = await create_test_form_registry(domain)
    doc = await create_test_document(domain)
    suffix = form_reg["suffix"]
    
    init_payload = {
        "form_registry_id": form_reg["form_registry_id"],
        "form_key": "draft-test-form",
        "title": "Draft Test Form",
    }
    
    await command_handler(
        domain, "initialize-form", init_payload, "document", doc["document_id"]
    )
    
    async with domain.statemgr.transaction():
        forms = await domain.statemgr.query(
            "form_submission",
            where={"document_id": doc["document_id"], "form_key": "draft-test-form"},
            limit=1
        )
        form_id = forms[0]._id
    
    submit_payload = {
        "payload": {
            f"first_name_{suffix}": {"value": "Draft"},
        },
        "status": "draft",
    }
    
    result = await command_handler(
        domain, "submit-form", submit_payload, "form_submission", form_id
    )
    
    async with domain.statemgr.transaction():
        form = await domain.statemgr.fetch("form_submission", form_id)
        assert form.status == "draft"
        assert form.locked is False


@mark.asyncio
async def test_submit_form_update_existing_elements(domain):
    """Test that submit updates existing elements."""
    form_reg = await create_test_form_registry(domain)
    doc = await create_test_document(domain)
    suffix = form_reg["suffix"]
    
    init_payload = {
        "form_registry_id": form_reg["form_registry_id"],
        "form_key": "update-elements-form",
        "title": "Update Elements Form",
        "initial_data": {
            f"first_name_{suffix}": {"value": "Original"},
        },
    }
    
    await command_handler(
        domain, "initialize-form", init_payload, "document", doc["document_id"]
    )
    
    async with domain.statemgr.transaction():
        forms = await domain.statemgr.query(
            "form_submission",
            where={"document_id": doc["document_id"], "form_key": "update-elements-form"},
            limit=1
        )
        form_id = forms[0]._id
    
    submit_payload = {
        "payload": {
            f"first_name_{suffix}": {"value": "Updated"},
        },
        "status": "draft",
    }
    
    await command_handler(
        domain, "submit-form", submit_payload, "form_submission", form_id
    )
    
    async with domain.statemgr.transaction():
        elements = await domain.statemgr.query(
            "form_element",
            where={"form_submission_id": form_id, "element_name": f"first_name_{suffix}"},
            limit=1
        )
        assert len(elements) == 1


@mark.asyncio
async def test_submit_form_with_replace(domain):
    """Test submit with replace=True removes elements not in payload."""
    form_reg = await create_test_form_registry(domain)
    doc = await create_test_document(domain)
    suffix = form_reg["suffix"]
    
    init_payload = {
        "form_registry_id": form_reg["form_registry_id"],
        "form_key": "replace-test-form",
        "title": "Replace Test Form",
        "initial_data": {
            f"first_name_{suffix}": {"value": "John"},
            f"last_name_{suffix}": {"value": "Doe"},
            f"email_{suffix}": {"value": "john@example.com"},
        },
    }
    
    await command_handler(
        domain, "initialize-form", init_payload, "document", doc["document_id"]
    )
    
    async with domain.statemgr.transaction():
        forms = await domain.statemgr.query(
            "form_submission",
            where={"document_id": doc["document_id"], "form_key": "replace-test-form"},
            limit=1
        )
        form_id = forms[0]._id
        
        elements = await domain.statemgr.query(
            "form_element",
            where={"form_submission_id": form_id}
        )
        assert len(elements) == 3
    
    submit_payload = {
        "payload": {
            f"first_name_{suffix}": {"value": "Jane"},
        },
        "replace": True,
        "status": "draft",
    }
    
    await command_handler(
        domain, "submit-form", submit_payload, "form_submission", form_id
    )
    
    async with domain.statemgr.transaction():
        elements = await domain.statemgr.query(
            "form_element",
            where={"form_submission_id": form_id}
        )
        assert len(elements) == 1
        assert elements[0].element_name == f"first_name_{suffix}"


@mark.asyncio
async def test_submit_locked_form_fails(domain):
    """Test that submitting a locked form fails."""
    form_reg = await create_test_form_registry(domain)
    doc = await create_test_document(domain)
    suffix = form_reg["suffix"]
    
    init_payload = {
        "form_registry_id": form_reg["form_registry_id"],
        "form_key": "locked-test-form",
        "title": "Locked Test Form",
    }
    
    await command_handler(
        domain, "initialize-form", init_payload, "document", doc["document_id"]
    )
    
    async with domain.statemgr.transaction():
        forms = await domain.statemgr.query(
            "form_submission",
            where={"document_id": doc["document_id"], "form_key": "locked-test-form"},
            limit=1
        )
        form_id = forms[0]._id
    
    submit_payload = {
        "payload": {f"first_name_{suffix}": {"value": "Test"}},
        "status": "submitted",
    }
    
    await command_handler(
        domain, "submit-form", submit_payload, "form_submission", form_id
    )
    
    submit_payload2 = {
        "payload": {f"first_name_{suffix}": {"value": "Modified"}},
        "status": "submitted",
    }
    
    with pytest.raises(BadRequestError) as exc_info:
        await command_handler(
            domain, "submit-form", submit_payload2, "form_submission", form_id
        )
    
    assert "locked" in str(exc_info.value).lower()


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

@mark.asyncio
async def test_full_form_workflow(domain):
    """Test complete form workflow: initialize -> save draft -> submit."""
    form_reg = await create_test_form_registry(domain)
    doc = await create_test_document(domain)
    suffix = form_reg["suffix"]
    
    init_payload = {
        "form_registry_id": form_reg["form_registry_id"],
        "form_key": "workflow-form",
        "title": "Application Form",
    }
    
    await command_handler(
        domain, "initialize-form", init_payload, "document", doc["document_id"]
    )
    
    async with domain.statemgr.transaction():
        forms = await domain.statemgr.query(
            "form_submission",
            where={"document_id": doc["document_id"], "form_key": "workflow-form"},
            limit=1
        )
        form_id = forms[0]._id
        assert forms[0].status == "draft"
    
    draft_payload = {
        "payload": {
            f"first_name_{suffix}": {"value": "John"},
        },
        "status": "draft",
    }
    
    await command_handler(
        domain, "submit-form", draft_payload, "form_submission", form_id
    )
    
    async with domain.statemgr.transaction():
        form = await domain.statemgr.fetch("form_submission", form_id)
        assert form.status == "draft"
        assert form.locked is False
    
    update_payload = {"title": "Updated Application Form"}
    
    await command_handler(
        domain, "update-form", update_payload, "form_submission", form_id
    )
    
    final_payload = {
        "payload": {
            f"first_name_{suffix}": {"value": "John"},
            f"last_name_{suffix}": {"value": "Smith"},
            f"email_{suffix}": {"value": "john.smith@example.com"},
        },
        "status": "submitted",
    }
    
    result = await command_handler(
        domain, "submit-form", final_payload, "form_submission", form_id
    )
    
    async with domain.statemgr.transaction():
        form = await domain.statemgr.fetch("form_submission", form_id)
        assert form.title == "Updated Application Form"
        assert form.status == "submitted"
        assert form.locked is True
        
        elements = await domain.statemgr.query(
            "form_element",
            where={"form_submission_id": form_id}
        )
        assert len(elements) == 3
