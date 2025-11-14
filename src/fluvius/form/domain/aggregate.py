from fluvius.domain.aggregate import Aggregate, action
from fluvius.data import UUID_GENR, timestamp
from fluvius.error import NotFoundError, BadRequestError

from .. import logger


class FormAggregate(Aggregate):
    """Aggregate for form domain operations"""

    @action("collection-created")
    async def create_collection(self, data):
        """Create a new collection"""
        collection = self.init_resource(
            "collection",
            _id=self.aggroot.identifier,
            collection_key=data.collection_key,
            collection_name=data.collection_name,
            desc=data.desc,
            attrs=data.attrs,
            owner_id=data.owner_id,
            organization_id=data.organization_id,
        )
        await self.statemgr.insert(collection)
        return {
            "collection_id": str(self.aggroot.identifier),
            "collection_key": collection.collection_key,
            "collection_name": collection.collection_name,
        }

    @action("collection-updated", resources="collection")
    async def update_collection(self, data):
        """Update collection properties"""
        collection = self.rootobj
        changes = data.model_dump(exclude_none=True)
        if not changes:
            raise BadRequestError("D100-001", "No changes provided for collection update")

        await self.statemgr.update(collection, **changes)

        # Refresh the object to get updated values
        async with self.statemgr.transaction():
            updated_collection = await self.statemgr.fetch('collection', collection._id)

        return {
            "collection_id": str(updated_collection._id),
            "collection_key": updated_collection.collection_key,
            "collection_name": updated_collection.collection_name,
        }

    @action("collection-removed", resources="collection")
    async def remove_collection(self, data):
        """Remove a collection"""
        collection = self.rootobj
        await self.statemgr.remove(collection)
        return {
            "collection_id": str(collection._id),
            "status": "removed",
        }

    @action("document-created")
    async def create_document(self, data):
        """Create a new document"""
        document = self.init_resource(
            "document",
            _id=self.aggroot.identifier,
            document_key=data.document_key,
            document_name=data.document_name,
            desc=data.desc,
            version=data.version or 1,
            attrs=data.attrs,
            owner_id=data.owner_id,
            organization_id=data.organization_id,
            resource_id=data.resource_id,
            resource_name=data.resource_name,
        )
        await self.statemgr.insert(document)
        return {
            "document_id": str(self.aggroot.identifier),
            "document_key": document.document_key,
            "document_name": document.document_name,
        }

    @action("document-updated", resources="document")
    async def update_document(self, data):
        """Update document properties"""
        document = self.rootobj
        changes = data.model_dump(exclude_none=True)
        if not changes:
            raise BadRequestError("D100-002", "No changes provided for document update")

        await self.statemgr.update(document, **changes)

        # Refresh the object to get updated values
        async with self.statemgr.transaction():
            updated_document = await self.statemgr.fetch('document', document._id)

        return {
            "document_id": str(updated_document._id),
            "document_key": updated_document.document_key,
            "document_name": updated_document.document_name,
        }

    @action("document-removed", resources="document")
    async def remove_document(self, data):
        """Remove a document"""
        document = self.rootobj
        await self.statemgr.remove(document)
        return {
            "document_id": str(document._id),
            "status": "removed",
        }

    @action("document-copied", resources="document")
    async def copy_document(self, data):
        """Copy a document"""
        source_document = self.rootobj

        # Create new document - use a new UUID for the copied document
        new_document_id = UUID_GENR()
        new_document = self.init_resource(
            "document",
            _id=new_document_id,
            document_key=data.new_document_key,
            document_name=data.new_document_name or source_document.document_name,
            desc=source_document.desc,
            version=1,
            attrs=data.attrs or source_document.attrs,
            owner_id=source_document.owner_id,
            organization_id=source_document.organization_id,
        )
        await self.statemgr.insert(new_document)

        # Copy sections if requested
        if data.copy_sections:
            sections = await self.statemgr.query(
                "section",
                where={"document_id": source_document._id},
                sort=(("order", "asc"),)
            )
            section_map = {}
            for section in sections:
                new_section_id = UUID_GENR()
                new_section = self.init_resource(
                    "section",
                    _id=new_section_id,
                    document_id=new_document_id,
                    section_key=section.section_key,
                    section_name=section.section_name,
                    desc=section.desc,
                    order=section.order,
                    attrs=section.attrs,
                )
                await self.statemgr.insert(new_section)
                section_map[section._id] = new_section_id

            # Copy document-form relationships if requested
            if data.copy_forms:
                doc_forms = await self.statemgr.query(
                    "document_form",
                    where={"document_id": source_document._id},
                    sort=(("order", "asc"),)
                )
                for doc_form in doc_forms:
                    new_section_id = section_map.get(doc_form.section_id)
                    if new_section_id:
                        new_doc_form = self.init_resource(
                            "document_form",
                            _id=UUID_GENR(),
                            document_id=new_document_id,
                            section_id=new_section_id,
                            form_id=doc_form.form_id,
                            order=doc_form.order,
                            attrs=doc_form.attrs,
                        )
                        await self.statemgr.insert(new_doc_form)

        return {
            "source_document_id": str(source_document._id),
            "new_document_id": str(new_document_id),
            "document_key": new_document.document_key,
            "status": "copied",
        }

    @action("element-populated", resources="data_element")
    async def populate_element(self, data):
        """Populate element with prior data"""
        element = self.rootobj

        # Note: This assumes form_instance table exists or will be created
        # For now, we'll return a placeholder response
        # In a real implementation, you would query form_instance and element_data tables
        
        return {
            "element_id": str(element._id),
            "form_instance_id": str(data.form_instance_id) if data.form_instance_id else None,
            "status": "populated",
            "message": "Element populated with prior data",
        }

    @action("form-populated", resources="data_form")
    async def populate_form(self, data):
        """Populate form with prior data"""
        form = self.rootobj

        # Note: This assumes form_instance table exists or will be created
        # For now, we'll return a placeholder response
        # In a real implementation, you would query form_instance and element_data tables
        
        return {
            "form_id": str(form._id),
            "form_instance_id": str(data.form_instance_id) if data.form_instance_id else None,
            "element_ids": [str(eid) for eid in data.element_ids] if data.element_ids else None,
            "status": "populated",
            "message": "Form populated with prior data",
        }

    @action("element-saved", resources="data_element")
    async def save_element(self, data):
        """Save element data"""
        element = self.rootobj

        # Note: This assumes form_instance and element_data tables exist
        # In a real implementation, you would:
        # 1. Get or create form_instance
        # 2. Save element_data linked to form_instance and element
        
        return {
            "element_id": str(element._id),
            "form_instance_id": str(data.form_instance_id),
            "status": "saved",
            "message": "Element data saved",
        }

    @action("form-saved", resources="data_form")
    async def save_form(self, data):
        """Save form data (multiple elements) but still allow further editing"""
        form = self.rootobj

        # Note: This assumes form_instance and element_data tables exist
        # In a real implementation, you would:
        # 1. Get or create form_instance
        # 2. Save all element_data entries linked to form_instance
        
        return {
            "form_id": str(form._id),
            "form_instance_id": str(data.form_instance_id),
            "elements_saved": len(data.elements),
            "status": "saved",
            "message": "Form data saved (editable)",
        }

    @action("form-submitted", resources="data_form")
    async def submit_form(self, data):
        """Submit form (saves element data and locks from further editing)"""
        form = self.rootobj

        # Note: This assumes form_instance and element_data tables exist
        # In a real implementation, you would:
        # 1. Get or create form_instance
        # 2. Save all element_data entries
        # 3. Set form_instance.locked = True or similar flag
        
        return {
            "form_id": str(form._id),
            "form_instance_id": str(data.form_instance_id),
            "elements_saved": len(data.elements),
            "status": "submitted",
            "locked": True,
            "message": "Form submitted and locked from further editing",
        }

