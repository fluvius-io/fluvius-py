from fluvius.data import serialize_mapping
from .domain import FormDomain
from . import datadef
from .datadef import (
    CreateCollectionData, UpdateCollectionData, RemoveCollectionData,
    CreateDocumentData, UpdateDocumentData, RemoveDocumentData, CopyDocumentData, MoveDocumentData,
    AddDocumentToCollectionData,
    PopulateElementData, PopulateFormData, SaveElementData, SaveFormData, SubmitFormData
)

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
        yield agg.create_response(serialize_mapping(document), _type="form-response")


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
        yield agg.create_response(serialize_mapping(document), _type="form-response")


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


class SaveElement(Command):
    """Save element data"""

    class Meta:
        key = 'save-element'
        name = 'Save Element'
        resources = ("element_definition",)
        tags = ["form", "element", "save"]
        auth_required = True
        description = "Save element data but still allow further editing"

    Data = SaveElementData

    async def _process(self, agg, stm, payload):
        result = await agg.save_element(payload)
        yield agg.create_response(serialize_mapping(result), _type="form-response")


class SaveForm(Command):
    """Save form data (multiple elements) but still allow further editing"""

    class Meta:
        key = 'save-form'
        name = 'Save Form'
        resources = ("form_definition",)
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
        resources = ("form_definition",)
        tags = ["form", "submit"]
        auth_required = True
        description = "Save element data and lock it from further editing"

    Data = SubmitFormData

    async def _process(self, agg, stm, payload):
        result = await agg.submit_form(payload)
        yield agg.create_response(serialize_mapping(result), _type="form-response")

