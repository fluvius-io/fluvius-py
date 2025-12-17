from fluvius.data import serialize_mapping, UUID_GENR
from .domain import FormDomain
from . import datadef
from .datadef import (
    CreateCollectionData, UpdateCollectionData, RemoveCollectionData,
    CreateDocumentData, UpdateDocumentData, RemoveDocumentData, CopyDocumentData, MoveDocumentData,
    AddDocumentToCollectionData,
    PopulateElementData,
    PopulateFormData,
    SaveFormData,
    SubmitFormData
)
from fluvius.domain.event import EventRecord 

Command = FormDomain.Command


class CreateCollection(Command):
    """Create a new collection"""

    class Meta:
        key = 'create-collection'
        name = 'Create Collection'
        resources = None
        tags = ["form", "collection", "create"]
        auth_required = True
        description = "Create a new collection for organizing documents"
        new_resource = True

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


class CreateDocument(Command):
    """Create a new document"""

    class Meta:
        key = 'create-document'
        name = 'Create Document'
        resources = None
        tags = ["form", "document", "create"]
        auth_required = True
        description = "Create a new document that can contain multiple forms"
        new_resource = True

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
            "organization_id": str(document.organization_id),
            "resource_id": str(document.resource_id) if document.resource_id else None,
            "resource_name": document.resource_name,
            "created_at": document.created_at.isoformat() if hasattr(document, 'created_at') and document.created_at else None,
            "updated_at": document.updated_at.isoformat() if hasattr(document, 'updated_at') and document.updated_at else None,
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
        description = "Copy a document with all its forms, sections, and elements"

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


class PopulateElement(Command):
    """Populate element with prior data"""

    class Meta:
        key = 'populate-element'
        name = 'Populate Element'
        resources = ("element_definition",)
        tags = ["form", "element", "populate"]
        auth_required = True
        description = "Repopulate an element with prior data from a form instance"

    Data = PopulateElementData

    async def _process(self, agg, stm, payload):
        result = await agg.populate_element(payload)
        yield agg.create_response(serialize_mapping(result), _type="form-response")


class PopulateForm(Command):
    """Populate form with prior data"""

    class Meta:
        key = 'populate-form'
        name = 'Populate Form'
        resources = ("form_definition",)
        tags = ["form", "populate"]
        auth_required = True
        description = "Repopulate a form (multiple elements) with prior data from a form instance"

    Data = PopulateFormData

    async def _process(self, agg, stm, payload):
        result = await agg.populate_form(payload)
        yield agg.create_response(serialize_mapping(result), _type="form-response")


class SaveForm(Command):
    """Save form data (multiple elements) but still allow further editing"""

    class Meta:
        key = 'save-form'
        name = 'Save Form'
        resources = ("document_form",)
        tags = ["form", "save"]
        auth_required = True
        description = "Save form data (multiple elements) but still allow further editing"

    Data = SaveFormData

    async def _process(self, agg, stm, payload):
        result = await agg.save_form(payload)
        yield agg.create_response(serialize_mapping(result), _type="form-response")


class SubmitForm(Command):
    """Submit form (saves element data and locks from further editing)"""

    class Meta:
        key = 'submit-form'
        name = 'Submit Form'
        resources = ("document_form",)
        tags = ["form", "submit"]
        auth_required = True
        description = "Save element data and lock it from further editing"

    Data = SubmitFormData

    async def _process(self, agg, stm, payload):
        result = await agg.submit_form(payload)
       
        yield EventRecord(
            _id=UUID_GENR(),
            event='approve-credit',
            src_cmd=agg.get_aggroot().identifier,
            args={},
            data={
                "event_name": "approve-credit",
                "wfdef_key": "loan-application-process",
                "workflow_id": "feee59ce-4f29-4a58-ae89-8c3cb4b856bf",
                "event_data": {
                    "resource_id": "a7e1c778-3ca5-405b-915d-f21aa30e8158",
                    "resource_name": "workflow_definition",
                    "step_selector": "f6f6fac6-4eb4-5939-894a-363bbd9a7b6f",
                    "additionalProp1": {}
                },
                "target_step_id": "f6f6fac6-4eb4-5939-894a-363bbd9a7b6f",
                "priority": "null"
            }
            
        )
        
        yield agg.create_response(result, _type="form-response")

