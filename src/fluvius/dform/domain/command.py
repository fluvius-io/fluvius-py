from fluvius.data import serialize_mapping
from .domain import FormDomain
from .datadef import (
    # Collection
    CreateCollectionData, UpdateCollectionData, RemoveCollectionData,
    # Document
    CreateDocumentData, UpdateDocumentData, RemoveDocumentData,
    CopyDocumentData, MoveDocumentData, AddDocumentToCollectionData,
    # Document Node
    CreateDocumentNodeData, UpdateDocumentNodeData, RemoveDocumentNodeData,
    # Form Commands
    InitializeFormData, UpdateFormData, RemoveFormData, SubmitFormData,
)

Command = FormDomain.Command


# ============================================================================
# COLLECTION COMMANDS
# ============================================================================

class CreateCollection(Command):
    """Create a new collection"""

    class Meta:
        key = 'create-collection'
        name = 'Create Collection'
        resources = None
        tags = ["form", "collection", "create"]
        auth_required = True
        description = "Create a new collection for organizing documents"
        resource_init = True

    Data = CreateCollectionData

    async def _process(self, agg, stm, payload):
        collection = await agg.create_collection(payload)
        yield agg.create_response(serialize_mapping(collection), _type="form-response")


class UpdateCollection(Command):
    """Update collection properties"""

    class Meta:
        key = 'update-collection'
        name = 'Update Collection'
        resources = ("collection",)
        tags = ["form", "collection", "update"]
        auth_required = True
        description = "Update collection properties"

    Data = UpdateCollectionData

    async def _process(self, agg, stm, payload):
        collection = await agg.update_collection(payload)
        yield agg.create_response(serialize_mapping(collection), _type="form-response")


class RemoveCollection(Command):
    """Remove a collection"""

    class Meta:
        key = 'remove-collection'
        name = 'Remove Collection'
        resources = ("collection",)
        tags = ["form", "collection", "remove"]
        auth_required = True
        description = "Remove a collection"

    Data = RemoveCollectionData

    async def _process(self, agg, stm, payload):
        result = await agg.remove_collection(payload)
        yield agg.create_response(serialize_mapping(result), _type="form-response")


# ============================================================================
# DOCUMENT COMMANDS
# ============================================================================

class CreateDocument(Command):
    """Create a new document"""

    class Meta:
        key = 'create-document'
        name = 'Create Document'
        resources = None
        tags = ["form", "document", "create"]
        auth_required = True
        description = "Create a new document that can contain multiple forms"
        resource_init = True

    Data = CreateDocumentData

    async def _process(self, agg, stm, payload):
        document = await agg.create_document(payload)
        document_dict = {
            "_id": str(document._id),
            "template_id": str(document.template_id),
            "document_key": document.document_key,
            "document_name": document.document_name,
            "desc": document.desc,
            "version": document.version,
            "organization_id": str(document.organization_id) if document.organization_id else None,
            "resource_id": str(document.resource_id) if document.resource_id else None,
            "resource_name": document.resource_name,
        }
        yield agg.create_response(document_dict, _type="document-response")


class UpdateDocument(Command):
    """Update document properties"""

    class Meta:
        key = 'update-document'
        name = 'Update Document'
        resources = ("document",)
        tags = ["form", "document", "update"]
        auth_required = True
        description = "Update document properties"

    Data = UpdateDocumentData

    async def _process(self, agg, stm, payload):
        document = await agg.update_document(payload)
        yield agg.create_response(document, _type="document-response")


class RemoveDocument(Command):
    """Remove a document"""

    class Meta:
        key = 'remove-document'
        name = 'Remove Document'
        resources = ("document",)
        tags = ["form", "document", "remove"]
        auth_required = True
        description = "Remove a document"

    Data = RemoveDocumentData

    async def _process(self, agg, stm, payload):
        result = await agg.remove_document(payload)
        yield agg.create_response(serialize_mapping(result), _type="form-response")


class CopyDocument(Command):
    """Copy a document with all its forms and elements"""

    class Meta:
        key = 'copy-document'
        name = 'Copy Document'
        resources = ("document",)
        tags = ["form", "document", "copy"]
        auth_required = True
        description = "Copy a document with all its nodes, form submissions, and elements"

    Data = CopyDocumentData

    async def _process(self, agg, stm, payload):
        result = await agg.copy_document(payload)
        yield agg.create_response(serialize_mapping(result), _type="form-response")


class MoveDocument(Command):
    """Move a document between collections"""

    class Meta:
        key = 'move-document'
        name = 'Move Document'
        resources = ("document",)
        tags = ["form", "document", "move"]
        auth_required = True
        description = "Move a document from one collection to another"

    Data = MoveDocumentData

    async def _process(self, agg, stm, payload):
        result = await agg.move_document(payload)
        yield agg.create_response(serialize_mapping(result), _type="form-response")


class AddDocumentToCollection(Command):
    """Add a document to an additional collection"""

    class Meta:
        key = 'add-document-to-collection'
        name = 'Add Document to Collection'
        resources = ("document",)
        tags = ["form", "document", "collection"]
        auth_required = True
        description = "Add a document to an additional collection (documents can be in multiple collections)"

    Data = AddDocumentToCollectionData

    async def _process(self, agg, stm, payload):
        result = await agg.add_document_to_collection(payload)
        yield agg.create_response(serialize_mapping(result), _type="form-response")


# ============================================================================
# DOCUMENT NODE COMMANDS
# ============================================================================

class CreateDocumentNode(Command):
    """Create a document node (section/content)"""

    class Meta:
        key = 'create-document-node'
        name = 'Create Document Node'
        resources = ("document",)
        tags = ["form", "document", "node", "create"]
        auth_required = True
        description = "Create a new document node (section or content block)"

    Data = CreateDocumentNodeData

    async def _process(self, agg, stm, payload):
        result = await agg.create_document_node(payload)
        yield agg.create_response(serialize_mapping(result), _type="form-response")


class UpdateDocumentNode(Command):
    """Update document node properties"""

    class Meta:
        key = 'update-document-node'
        name = 'Update Document Node'
        resources = ("document_node",)
        tags = ["form", "document", "node", "update"]
        auth_required = True
        description = "Update document node properties"

    Data = UpdateDocumentNodeData

    async def _process(self, agg, stm, payload):
        result = await agg.update_document_node(payload)
        yield agg.create_response(serialize_mapping(result), _type="form-response")


class RemoveDocumentNode(Command):
    """Remove a document node"""

    class Meta:
        key = 'remove-document-node'
        name = 'Remove Document Node'
        resources = ("document_node",)
        tags = ["form", "document", "node", "remove"]
        auth_required = True
        description = "Remove a document node"

    Data = RemoveDocumentNodeData

    async def _process(self, agg, stm, payload):
        result = await agg.remove_document_node(payload)
        yield agg.create_response(serialize_mapping(result), _type="form-response")


# ============================================================================
# FORM COMMANDS
# ============================================================================

class InitializeForm(Command):
    """
    Create and initialize a form submission with element structure.
    
    This command creates a new form submission from a form registry entry,
    sets up the form elements, and optionally populates them with prior data.
    """

    class Meta:
        key = 'initialize-form'
        name = 'Initialize Form'
        resources = ("document",)
        tags = ["form", "create", "initialize"]
        auth_required = True
        description = "Create and initialize a form submission with element structure"
        resource_init = True

    Data = InitializeFormData

    async def _process(self, agg, stm, payload):
        result = await agg.initialize_form(payload)
        yield agg.create_response(serialize_mapping(result), _type="form-response")


class UpdateForm(Command):
    """Update form properties"""

    class Meta:
        key = 'update-form'
        name = 'Update Form'
        resources = ("form_submission",)
        tags = ["form", "update"]
        auth_required = True
        description = "Update form properties"

    Data = UpdateFormData

    async def _process(self, agg, stm, payload):
        result = await agg.update_form(payload)
        yield agg.create_response(serialize_mapping(result), _type="form-response")


class RemoveForm(Command):
    """Remove a form"""

    class Meta:
        key = 'remove-form'
        name = 'Remove Form'
        resources = ("form_submission",)
        tags = ["form", "remove"]
        auth_required = True
        description = "Remove a form"

    Data = RemoveFormData

    async def _process(self, agg, stm, payload):
        result = await agg.remove_form(payload)
        yield agg.create_response(serialize_mapping(result), _type="form-response")


class SubmitForm(Command):
    """
    Submit/save form data.
    
    This command saves element data and sets form status.
    Use status="draft" to save without submitting, or status="submitted" to lock.
    """

    class Meta:
        key = 'submit-form'
        name = 'Submit Form'
        resources = ("form_submission",)
        tags = ["form", "submit", "save"]
        auth_required = True
        description = "Submit/save form data with configurable status"

    Data = SubmitFormData

    async def _process(self, agg, stm, payload):
        result = await agg.submit_form(payload)
        yield agg.create_response(result, _type="form-response")
