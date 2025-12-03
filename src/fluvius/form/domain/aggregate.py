from fluvius.domain.aggregate import Aggregate, action
from fluvius.data import UUID_GENR, timestamp
from fluvius.error import NotFoundError, BadRequestError
from fluvius.form.element import get_element_type, ElementDataManager

from .. import logger


class FormAggregate(Aggregate):
    """Aggregate for form domain operations"""

    # ============================================================================
    # TEMPLATE DEFINITION METHODS
    # ============================================================================

    @action("template-created")
    async def create_template(self, data):
        """Create a new document template"""
        template = self.init_resource(
            "template",
            _id=self.aggroot.identifier,
            template_key=data.template_key,
            template_name=data.template_name,
            desc=data.desc,
            version=data.version or 1,
            owner_id=data.owner_id,
            organization_id=data.organization_id,
        )
        await self.statemgr.insert(template)
        
        # Add template to collections if specified
        collection_ids = []
        if data.collection_id:
            collection_ids.append(data.collection_id)
        if data.collection_ids:
            collection_ids.extend(data.collection_ids)
        
        # Remove duplicates
        seen = set()
        unique_collection_ids = []
        for cid in collection_ids:
            if cid not in seen:
                seen.add(cid)
                unique_collection_ids.append(cid)
        
        added_collection_ids = []
        for collection_id in unique_collection_ids:
            collection = await self.statemgr.fetch('collection', collection_id)
            if not collection:
                raise NotFoundError(
                    "F00.201",
                    f"Collection not found: {collection_id}",
                    None
                )
            
            # Check if template is already in this collection
            existing = await self.statemgr.query(
                "template_collection",
                where={"template_id": template._id, "collection_id": collection_id},
                limit=1
            )
            if existing:
                raise BadRequestError(
                    "F00.203",
                    f"Template {template._id} is already in collection {collection_id}",
                    None
                )
            
            order = data.order
            if order is None:
                max_order = await self.statemgr.query(
                    "template_collection",
                    where={"collection_id": collection_id},
                    sort=(("order", "desc"),),
                    limit=1
                )
                order = (max_order[0].order + 1) if max_order else 0
            
            template_collection = self.init_resource(
                "template_collection",
                _id=UUID_GENR(),
                template_id=template._id,
                collection_id=collection_id,
                order=order,
            )
            await self.statemgr.insert(template_collection)
            added_collection_ids.append(collection_id)
        
        return {
            "template_id": str(self.aggroot.identifier),
            "template_key": template.template_key,
            "template_name": template.template_name,
            "collection_ids": [str(cid) for cid in added_collection_ids],
        }

    @action("template-updated", resources="template")
    async def update_template(self, data):
        """Update template properties"""
        template = self.rootobj
        changes = data.model_dump(exclude_none=True)
        if not changes:
            raise BadRequestError("F00.001", "No changes provided for template update")

        await self.statemgr.update(template, **changes)

        async with self.statemgr.transaction():
            updated_template = await self.statemgr.fetch('template', template._id)

        return {
            "template_id": str(updated_template._id),
            "template_key": updated_template.template_key,
            "template_name": updated_template.template_name,
        }

    @action("template-removed", resources="template")
    async def remove_template(self, data):
        """Remove a template"""
        template = self.rootobj
        await self.statemgr.remove(template)
        return {
            "template_id": str(template._id),
            "status": "removed",
        }

    @action("section-definition-created", resources="template")
    async def create_section_definition(self, data):
        """Create a section definition within a template"""
        template = self.rootobj
        section_def = self.init_resource(
            "section_definition",
            _id=UUID_GENR(),
            template_id=template._id,
            section_key=data.section_key,
            section_name=data.section_name,
            desc=data.desc,
            order=data.order or 0,
        )
        await self.statemgr.insert(section_def)
        return {
            "section_definition_id": str(section_def._id),
            "section_key": section_def.section_key,
            "section_name": section_def.section_name,
        }

    @action("section-definition-updated", resources="section_definition")
    async def update_section_definition(self, data):
        """Update section definition properties"""
        section_def = self.rootobj
        changes = data.model_dump(exclude_none=True)
        if not changes:
            raise BadRequestError("F00.001", "No changes provided for section definition update")

        await self.statemgr.update(section_def, **changes)

        async with self.statemgr.transaction():
            updated = await self.statemgr.fetch('section_definition', section_def._id)

        return {
            "section_definition_id": str(updated._id),
            "section_key": updated.section_key,
            "section_name": updated.section_name,
        }

    @action("section-definition-removed", resources="section_definition")
    async def remove_section_definition(self, data):
        """Remove a section definition"""
        section_def = self.rootobj
        await self.statemgr.remove(section_def)
        return {
            "section_definition_id": str(section_def._id),
            "status": "removed",
        }

    @action("form-definition-created", resources="section_definition")
    async def create_form_definition(self, data):
        """Create a form definition within a section definition"""
        section_def = self.rootobj
        form_def = self.init_resource(
            "form_definition",
            _id=UUID_GENR(),
            section_definition_id=section_def._id,
            form_key=data.form_key,
            title=data.title,
            desc=data.desc,
            order=data.order or 0,
        )
        await self.statemgr.insert(form_def)
        return {
            "form_definition_id": str(form_def._id),
            "form_key": form_def.form_key,
            "title": form_def.title,
        }

    @action("form-definition-updated", resources="form_definition")
    async def update_form_definition(self, data):
        """Update form definition properties"""
        form_def = self.rootobj
        changes = data.model_dump(exclude_none=True)
        if not changes:
            raise BadRequestError("F00.001", "No changes provided for form definition update")

        await self.statemgr.update(form_def, **changes)

        async with self.statemgr.transaction():
            updated = await self.statemgr.fetch('form_definition', form_def._id)

        return {
            "form_definition_id": str(updated._id),
            "form_key": updated.form_key,
            "title": updated.title,
        }

    @action("form-definition-removed", resources="form_definition")
    async def remove_form_definition(self, data):
        """Remove a form definition"""
        form_def = self.rootobj
        await self.statemgr.remove(form_def)
        return {
            "form_definition_id": str(form_def._id),
            "status": "removed",
        }

    @action("element-group-definition-created", resources="form_definition")
    async def create_element_group_definition(self, data):
        """Create an element group definition within a form definition"""
        form_def = self.rootobj
        group_def = self.init_resource(
            "element_group_definition",
            _id=UUID_GENR(),
            form_definition_id=form_def._id,
            group_key=data.group_key,
            group_name=data.group_name,
            desc=data.desc,
            order=data.order or 0,
        )
        await self.statemgr.insert(group_def)
        return {
            "element_group_definition_id": str(group_def._id),
            "group_key": group_def.group_key,
            "group_name": group_def.group_name,
        }

    @action("element-group-definition-updated", resources="element_group_definition")
    async def update_element_group_definition(self, data):
        """Update element group definition properties"""
        group_def = self.rootobj
        changes = data.model_dump(exclude_none=True)
        if not changes:
            raise BadRequestError("F00.001", "No changes provided for element group definition update")

        await self.statemgr.update(group_def, **changes)

        async with self.statemgr.transaction():
            updated = await self.statemgr.fetch('element_group_definition', group_def._id)

        return {
            "element_group_definition_id": str(updated._id),
            "group_key": updated.group_key,
            "group_name": updated.group_name,
        }

    @action("element-group-definition-removed", resources="element_group_definition")
    async def remove_element_group_definition(self, data):
        """Remove an element group definition"""
        group_def = self.rootobj
        await self.statemgr.remove(group_def)
        return {
            "element_group_definition_id": str(group_def._id),
            "status": "removed",
        }

    @action("element-definition-created", resources="element_group_definition")
    async def create_element_definition(self, data):
        """Create an element definition within an element group definition"""
        group_def = self.rootobj
        
        # Verify element type exists
        element_type = await self.statemgr.fetch('element_type', data.element_type_id)
        if not element_type:
            raise NotFoundError(
                "F00.204",
                f"Element type not found: {data.element_type_id}",
                None
            )
        
        element_def = self.init_resource(
            "element_definition",
            _id=UUID_GENR(),
            element_group_definition_id=group_def._id,
            element_type_id=data.element_type_id,
            element_key=data.element_key,
            element_label=data.element_label,
            order=data.order or 0,
            required=data.required or False,
            validation_rules=data.validation_rules,
            resource_id=data.resource_id,
            resource_name=data.resource_name,
        )
        await self.statemgr.insert(element_def)
        return {
            "element_definition_id": str(element_def._id),
            "element_key": element_def.element_key,
            "element_label": element_def.element_label,
        }

    @action("element-definition-updated", resources="element_definition")
    async def update_element_definition(self, data):
        """Update element definition properties"""
        element_def = self.rootobj
        changes = data.model_dump(exclude_none=True)
        if not changes:
            raise BadRequestError("F00.001", "No changes provided for element definition update")

        await self.statemgr.update(element_def, **changes)

        async with self.statemgr.transaction():
            updated = await self.statemgr.fetch('element_definition', element_def._id)

        return {
            "element_definition_id": str(updated._id),
            "element_key": updated.element_key,
            "element_label": updated.element_label,
        }

    @action("element-definition-removed", resources="element_definition")
    async def remove_element_definition(self, data):
        """Remove an element definition"""
        element_def = self.rootobj
        await self.statemgr.remove(element_def)
        return {
            "element_definition_id": str(element_def._id),
            "status": "removed",
        }

    # ============================================================================
    # DATA INSTANCE METHODS
    # ============================================================================

    @action("collection-created")
    async def create_collection(self, data):
        """Create a new collection"""
        collection = self.init_resource(
            "collection",
            _id=self.aggroot.identifier,
            collection_key=data.collection_key,
            collection_name=data.collection_name,
            desc=data.desc,
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
            raise BadRequestError("F00.001", "No changes provided for collection update")

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
        """Create a new document instance from a template and optionally add it to collections"""
        # Verify template exists
        template = await self.statemgr.fetch('template', data.template_id)
        if not template:
            raise NotFoundError(
                "F00.205",
                f"Template not found: {data.template_id}",
                None
            )
        
        document = self.init_resource(
            "document",
            _id=self.aggroot.identifier,
            template_id=data.template_id,
            document_key=data.document_key,
            document_name=data.document_name,
            desc=data.desc,
            version=data.version or 1,
            owner_id=data.owner_id,
            organization_id=data.organization_id,
            resource_id=data.resource_id,
            resource_name=data.resource_name,
        )
        await self.statemgr.insert(document)
        
        # Create section instances from section definitions in the template
        # Note: Form instances and element instances are created lazily when forms are populated/saved
        section_definitions = await self.statemgr.query(
            "section_definition",
            where={"template_id": data.template_id},
            sort=(("order", "asc"),)
        )
        
        for section_def in section_definitions:
            section_instance = self.init_resource(
                "section_instance",
                _id=UUID_GENR(),
                document_id=document._id,
                section_definition_id=section_def._id,
                instance_key=section_def.section_key,  # Use section_key as default instance_key
                instance_name=section_def.section_name,
                order=section_def.order,
            )
            await self.statemgr.insert(section_instance)
        
        # Collect collection IDs to add document to
        collection_ids = []
        if data.collection_id:
            collection_ids.append(data.collection_id)
        if data.collection_ids:
            collection_ids.extend(data.collection_ids)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_collection_ids = []
        for cid in collection_ids:
            if cid not in seen:
                seen.add(cid)
                unique_collection_ids.append(cid)
        
        added_collection_ids = []
        for collection_id in unique_collection_ids:
            # Verify collection exists
            collection = await self.statemgr.fetch('collection', collection_id)
            if not collection:
                raise NotFoundError(
                    "F00.201",
                    f"Collection not found: {collection_id}",
                    None
                )
            
            # Check if document is already in this collection
            existing = await self.statemgr.query(
                "document_collection",
                where={
                    "document_id": self.aggroot.identifier,
                    "collection_id": collection_id
                },
                limit=1
            )
            
            if not existing:
                # Determine order - if not specified, use max order + 1
                if data.order is None:
                    max_order_docs = await self.statemgr.query(
                        "document_collection",
                        where={"collection_id": collection_id},
                        sort=(("order", "desc"),),
                        limit=1
                    )
                    order = (max_order_docs[0].order + 1) if max_order_docs else 0
                else:
                    order = data.order
                
                # Add document to collection
                doc_collection = self.init_resource(
                    "document_collection",
                    _id=UUID_GENR(),
                    document_id=self.aggroot.identifier,
                    collection_id=collection_id,
                    order=order,
                )
                await self.statemgr.insert(doc_collection)
                added_collection_ids.append(collection_id)
        
        return {
            "document_id": str(self.aggroot.identifier),
            "document_key": document.document_key,
            "document_name": document.document_name,
            "collection_ids": [str(cid) for cid in added_collection_ids],
        }

    @action("document-updated", resources="document")
    async def update_document(self, data):
        """Update document properties"""
        document = self.rootobj
        changes = data.model_dump(exclude_none=True)
        if not changes:
            raise BadRequestError("F00.002", "No changes provided for document update")

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
        """Copy a document with all its section instances, form instances, and element instances"""
        source_document = self.rootobj

        # Create new document - use a new UUID for the copied document
        new_document_id = UUID_GENR()
        new_document = self.init_resource(
            "document",
            _id=new_document_id,
            template_id=source_document.template_id,  # Same template
            document_key=data.new_document_key,
            document_name=data.new_document_name or source_document.document_name,
            desc=source_document.desc,
            version=1,
            owner_id=source_document.owner_id,
            organization_id=source_document.organization_id,
            resource_id=source_document.resource_id,
            resource_name=source_document.resource_name,
        )
        await self.statemgr.insert(new_document)

        element_data_mgr = ElementDataManager()

        # Copy section instances if requested
        if data.copy_sections:
            section_instances = await self.statemgr.query(
                "section_instance",
                where={"document_id": source_document._id},
                sort=(("order", "asc"),)
            )
            section_instance_map = {}
            for section_instance in section_instances:
                new_section_instance_id = UUID_GENR()
                new_section_instance = self.init_resource(
                    "section_instance",
                    _id=new_section_instance_id,
                    document_id=new_document_id,
                    section_definition_id=section_instance.section_definition_id,
                    instance_key=section_instance.instance_key,
                    instance_name=section_instance.instance_name,
                    order=section_instance.order,
                )
                await self.statemgr.insert(new_section_instance)
                section_instance_map[section_instance._id] = new_section_instance_id

            # Copy form instances if requested
            if data.copy_forms:
                for old_section_instance_id, new_section_instance_id in section_instance_map.items():
                    async with element_data_mgr.transaction():
                        form_instances = await element_data_mgr.query(
                            "form_instance",
                            where={"section_instance_id": old_section_instance_id},
                        )
                        form_instance_map = {}
                        
                        for form_instance in form_instances:
                            new_form_instance_id = UUID_GENR()
                            new_form_instance = element_data_mgr.create(
                                "form_instance",
                                _id=new_form_instance_id,
                                section_instance_id=new_section_instance_id,
                                form_definition_id=form_instance.form_definition_id,
                                instance_key=form_instance.instance_key,
                                instance_name=form_instance.instance_name,
                                locked=False,  # New instance is not locked
                                attrs=form_instance.attrs,
                                owner_id=form_instance.owner_id,
                                organization_id=form_instance.organization_id,
                            )
                            await element_data_mgr.insert(new_form_instance)
                            form_instance_map[form_instance._id] = new_form_instance_id
                            
                            # Copy element group instances if requested
                            if data.copy_element_groups:
                                element_group_instances = await element_data_mgr.query(
                                    "element_group_instance",
                                    where={"form_instance_id": form_instance._id},
                                )
                                element_group_instance_map = {}
                                
                                for group_instance in element_group_instances:
                                    new_group_instance_id = UUID_GENR()
                                    new_group_instance = element_data_mgr.create(
                                        "element_group_instance",
                                        _id=new_group_instance_id,
                                        form_instance_id=new_form_instance_id,
                                        element_group_definition_id=group_instance.element_group_definition_id,
                                        instance_key=group_instance.instance_key,
                                        instance_name=group_instance.instance_name,
                                        order=group_instance.order,
                                    )
                                    await element_data_mgr.insert(new_group_instance)
                                    element_group_instance_map[group_instance._id] = new_group_instance_id
                                    
                                    # Copy element instances if requested
                                    if data.copy_elements:
                                        element_instances = await element_data_mgr.query(
                                            "element_instance",
                                            where={"element_group_instance_id": group_instance._id},
                                        )
                                        
                                        for element_instance in element_instances:
                                            new_element_instance = element_data_mgr.create(
                                                "element_instance",
                                                _id=UUID_GENR(),
                                                element_group_instance_id=new_group_instance_id,
                                                element_definition_id=element_instance.element_definition_id,
                                                instance_key=element_instance.instance_key,
                                                data=element_instance.data,
                                                attrs=element_instance.attrs,
                                            )
                                            await element_data_mgr.insert(new_element_instance)

        # Add copied document to target collection if specified
        if data.target_collection_id:
            # Verify target collection exists
            target_collection = await self.statemgr.fetch('collection', data.target_collection_id)
            if not target_collection:
                raise NotFoundError(
                    "F00.201",
                    f"Target collection not found: {data.target_collection_id}",
                    None
                )
            
            # Check if document is already in target collection
            existing_in_target = await self.statemgr.query(
                "document_collection",
                where={
                    "document_id": new_document_id,
                    "collection_id": data.target_collection_id
                },
                limit=1
            )
            
            if not existing_in_target:
                # Determine order - if not specified, use max order + 1
                if data.order is None:
                    max_order_docs = await self.statemgr.query(
                        "document_collection",
                        where={"collection_id": data.target_collection_id},
                        sort=(("order", "desc"),),
                        limit=1
                    )
                    order = (max_order_docs[0].order + 1) if max_order_docs else 0
                else:
                    order = data.order
                
                # Add to target collection
                doc_collection = self.init_resource(
                    "document_collection",
                    _id=UUID_GENR(),
                    document_id=new_document_id,
                    collection_id=data.target_collection_id,
                    order=order,
                )
                await self.statemgr.insert(doc_collection)

        return {
            "source_document_id": str(source_document._id),
            "new_document_id": str(new_document_id),
            "document_key": new_document.document_key,
            "target_collection_id": str(data.target_collection_id) if data.target_collection_id else None,
            "status": "copied",
        }

    @action("document-moved", resources="document")
    async def move_document(self, data):
        """Move a document between collections"""
        document = self.rootobj
        
        # Verify target collection exists
        target_collection = await self.statemgr.fetch('collection', data.target_collection_id)
        if not target_collection:
            raise NotFoundError(
                "F00.201",
                f"Target collection not found: {data.target_collection_id}",
                None
            )
        
        # Remove from source collection if specified
        if data.source_collection_id:
            # Verify source collection exists
            source_collection = await self.statemgr.fetch('collection', data.source_collection_id)
            if not source_collection:
                raise NotFoundError(
                    "F00.202",
                    f"Source collection not found: {data.source_collection_id}",
                    None
                )
            
            # Find and remove existing document_collection relationship
            existing = await self.statemgr.query(
                "document_collection",
                where={
                    "document_id": document._id,
                    "collection_id": data.source_collection_id
                },
                limit=1
            )
            if existing:
                await self.statemgr.remove(existing[0])
        else:
            # Remove from all collections
            all_collections = await self.statemgr.query(
                "document_collection",
                where={"document_id": document._id}
            )
            for doc_col in all_collections:
                await self.statemgr.remove(doc_col)
        
        # Check if document is already in target collection
        existing_in_target = await self.statemgr.query(
            "document_collection",
            where={
                "document_id": document._id,
                "collection_id": data.target_collection_id
            },
            limit=1
        )
        
        if not existing_in_target:
            # Determine order - if not specified, use max order + 1
            if data.order is None:
                max_order_docs = await self.statemgr.query(
                    "document_collection",
                    where={"collection_id": data.target_collection_id},
                    sort=(("order", "desc"),),
                    limit=1
                )
                order = (max_order_docs[0].order + 1) if max_order_docs else 0
            else:
                order = data.order
            
            # Add to target collection
            doc_collection = self.init_resource(
                "document_collection",
                _id=UUID_GENR(),
                document_id=document._id,
                collection_id=data.target_collection_id,
                order=order,
            )
            await self.statemgr.insert(doc_collection)
        
        return {
            "document_id": str(document._id),
            "source_collection_id": str(data.source_collection_id) if data.source_collection_id else None,
            "target_collection_id": str(data.target_collection_id),
            "status": "moved",
        }

    @action("document-added-to-collection", resources="document")
    async def add_document_to_collection(self, data):
        """Add a document to an additional collection"""
        document = self.rootobj
        
        # Verify collection exists
        collection = await self.statemgr.fetch('collection', data.collection_id)
        if not collection:
            raise NotFoundError(
                "F00.201",
                f"Collection not found: {data.collection_id}",
                None
            )
        
        # Check if document is already in this collection
        existing = await self.statemgr.query(
            "document_collection",
            where={
                "document_id": document._id,
                "collection_id": data.collection_id
            },
            limit=1
        )
        
        if existing:
            raise BadRequestError(
                "F00.203",
                f"Document is already in collection: {data.collection_id}",
                None
            )
        
        # Determine order - if not specified, use max order + 1
        if data.order is None:
            max_order_docs = await self.statemgr.query(
                "document_collection",
                where={"collection_id": data.collection_id},
                sort=(("order", "desc"),),
                limit=1
            )
            order = (max_order_docs[0].order + 1) if max_order_docs else 0
        else:
            order = data.order
        
        # Add document to collection
        doc_collection = self.init_resource(
            "document_collection",
            _id=UUID_GENR(),
            document_id=document._id,
            collection_id=data.collection_id,
            order=order,
        )
        await self.statemgr.insert(doc_collection)
        
        return {
            "document_id": str(document._id),
            "collection_id": str(data.collection_id),
            "status": "added",
        }

    @action("element-populated", resources="element_definition")
    async def populate_element(self, data):
        """Populate element with prior data from an element group instance"""
        element_def = self.rootobj
        
        element_data_mgr = ElementDataManager()
        
        result = {
            "element_definition_id": str(element_def._id),
            "element_group_instance_id": str(data.element_group_instance_id) if data.element_group_instance_id else None,
            "status": "populated",
            "data": None,
        }
        
        if data.element_group_instance_id:
            async with element_data_mgr.transaction():
                # Find existing element instance data
                element_instances = await element_data_mgr.query(
                    "element_instance",
                    where={
                        "element_group_instance_id": data.element_group_instance_id,
                        "element_definition_id": element_def._id
                    },
                    limit=1
                )
                if element_instances:
                    result["data"] = element_instances[0].data
        
        return result

    @action("form-populated", resources="form_definition")
    async def populate_form(self, data):
        """Populate form with prior data from a form instance"""
        form_def = self.rootobj
        
        element_data_mgr = ElementDataManager()
        
        result = {
            "form_definition_id": str(form_def._id),
            "form_instance_id": str(data.form_instance_id) if data.form_instance_id else None,
            "element_definition_ids": [str(eid) for eid in data.element_definition_ids] if data.element_definition_ids else None,
            "status": "populated",
            "elements": [],
        }
        
        if data.form_instance_id:
            async with element_data_mgr.transaction():
                # Get all element group instances for this form instance
                element_group_instances = await element_data_mgr.query(
                    "element_group_instance",
                    where={"form_instance_id": data.form_instance_id}
                )
                
                for group_instance in element_group_instances:
                    # Get all element instances for this group
                    element_instances = await element_data_mgr.query(
                        "element_instance",
                        where={"element_group_instance_id": group_instance._id}
                    )
                    
                    for element_instance in element_instances:
                        # Filter by element_definition_ids if provided
                        if data.element_definition_ids and element_instance.element_definition_id not in data.element_definition_ids:
                            continue
                        
                        result["elements"].append({
                            "element_definition_id": str(element_instance.element_definition_id),
                            "element_group_instance_id": str(group_instance._id),
                            "instance_key": element_instance.instance_key,
                            "data": element_instance.data,
                        })
        
        return result

    @action("element-saved", resources="element_definition")
    async def save_element(self, data):
        """Save element data with validation"""
        element_def = self.rootobj

        # Get element type from database
        element_type_record = await self.statemgr.fetch('element_type', element_def.element_type_id)

        # Get element type class for validation
        try:
            element_type_cls = get_element_type(element_type_record.type_key)
        except (RuntimeError, NotFoundError):
            # Element type not registered, skip validation
            element_type_cls = None

        # Validate data using element type class
        validated_data = data.data
        if element_type_cls:
            validated_data = element_type_cls.validate_data(data.data)

        # Get element data manager
        element_data_mgr = ElementDataManager()

        # Use transaction context for element data operations
        async with element_data_mgr.transaction():
            # Check if element instance already exists
            existing_instances = await element_data_mgr.query(
                "element_instance",
                where={
                    "element_group_instance_id": data.element_group_instance_id,
                    "element_definition_id": element_def._id
                },
                limit=1
            )

            if existing_instances:
                # Update existing element instance
                element_instance = existing_instances[0]
                await element_data_mgr.update(
                    element_instance,
                    data=validated_data,
                    attrs=data.attrs,
                    **self.audit_updated()
                )
            else:
                # Create new element instance
                element_instance = element_data_mgr.create(
                    "element_instance",
                    _id=UUID_GENR(),
                    element_group_instance_id=data.element_group_instance_id,
                    element_definition_id=element_def._id,
                    instance_key=data.instance_key,
                    data=validated_data,
                    attrs=data.attrs,
                )
                await element_data_mgr.insert(element_instance)
        
        return {
            "element_definition_id": str(element_def._id),
            "element_group_instance_id": str(data.element_group_instance_id),
            "element_instance_id": str(element_instance._id),
            "status": "saved",
            "message": "Element data saved",
        }

    @action("form-saved", resources="form_definition")
    async def save_form(self, data):
        """Save form data (multiple elements) but still allow further editing"""
        form_def = self.rootobj

        # Get element data manager
        element_data_mgr = ElementDataManager()

        # Use transaction context for element data operations
        async with element_data_mgr.transaction():
            # Verify form instance exists
            form_instance = await element_data_mgr.fetch('form_instance', data.form_instance_id)
            if not form_instance:
                raise NotFoundError(
                    "F00.206",
                    f"Form instance not found: {data.form_instance_id}",
                    None
                )

            # Save each element data
            saved_count = 0
            for element_data in data.elements:
                element_definition_id = element_data.get("element_definition_id")
                element_group_instance_id = element_data.get("element_group_instance_id")
                instance_key = element_data.get("instance_key")
                element_data_dict = element_data.get("data", {})
                element_attrs = element_data.get("attrs")

                if not element_definition_id or not element_group_instance_id:
                    continue

                # Get element definition from database
                element_def = await self.statemgr.fetch('element_definition', element_definition_id)

                # Get element type for validation
                element_type_record = await self.statemgr.fetch('element_type', element_def.element_type_id)

                # Validate data
                validated_data = element_data_dict
                try:
                    element_type_cls = get_element_type(element_type_record.type_key)
                    validated_data = element_type_cls.validate_data(element_data_dict)
                except (RuntimeError, NotFoundError):
                    # Element type not registered, skip validation
                    pass

                # Check if element instance already exists
                existing_instances = await element_data_mgr.query(
                    "element_instance",
                    where={
                        "element_group_instance_id": element_group_instance_id,
                        "element_definition_id": element_definition_id
                    },
                    limit=1
                )

                if existing_instances:
                    # Update existing
                    await element_data_mgr.update(
                        existing_instances[0],
                        data=validated_data,
                        attrs=element_attrs,
                        **self.audit_updated()
                    )
                else:
                    # Create new
                    new_element_instance = element_data_mgr.create(
                        "element_instance",
                        _id=UUID_GENR(),
                        element_group_instance_id=element_group_instance_id,
                        element_definition_id=element_definition_id,
                        instance_key=instance_key or f"element-{str(element_definition_id)[:8]}",
                        data=validated_data,
                        attrs=element_attrs,
                    )
                    await element_data_mgr.insert(new_element_instance)

                saved_count += 1
        
        return {
            "form_definition_id": str(form_def._id),
            "form_instance_id": str(data.form_instance_id),
            "elements_saved": saved_count,
            "status": "saved",
            "message": "Form data saved (editable)",
        }

    @action("form-submitted", resources="form_definition")
    async def submit_form(self, data):
        """Submit form (saves element data and locks from further editing)"""
        form_def = self.rootobj

        # Get element data manager
        element_data_mgr = ElementDataManager()

        # Use transaction context for element data operations
        async with element_data_mgr.transaction():
            # Verify form instance exists
            form_instance = await element_data_mgr.fetch('form_instance', data.form_instance_id)
            if not form_instance:
                raise NotFoundError(
                    "F00.206",
                    f"Form instance not found: {data.form_instance_id}",
                    None
                )

            # Save each element data
            saved_count = 0
            for element_data in data.elements:
                element_definition_id = element_data.get("element_definition_id")
                element_group_instance_id = element_data.get("element_group_instance_id")
                instance_key = element_data.get("instance_key")
                element_data_dict = element_data.get("data", {})
                element_attrs = element_data.get("attrs")

                if not element_definition_id or not element_group_instance_id:
                    continue

                # Get element definition from database
                element_def = await self.statemgr.fetch('element_definition', element_definition_id)

                # Get element type for validation
                element_type_record = await self.statemgr.fetch('element_type', element_def.element_type_id)

                # Validate data
                validated_data = element_data_dict
                try:
                    element_type_cls = get_element_type(element_type_record.type_key)
                    validated_data = element_type_cls.validate_data(element_data_dict)
                except (RuntimeError, NotFoundError):
                    # Element type not registered, skip validation
                    pass

                # Check if element instance already exists
                existing_instances = await element_data_mgr.query(
                    "element_instance",
                    where={
                        "element_group_instance_id": element_group_instance_id,
                        "element_definition_id": element_definition_id
                    },
                    limit=1
                )

                if existing_instances:
                    # Update existing
                    await element_data_mgr.update(
                        existing_instances[0],
                        data=validated_data,
                        attrs=element_attrs,
                        **self.audit_updated()
                    )
                else:
                    # Create new
                    new_element_instance = element_data_mgr.create(
                        "element_instance",
                        _id=UUID_GENR(),
                        element_group_instance_id=element_group_instance_id,
                        element_definition_id=element_definition_id,
                        instance_key=instance_key or f"element-{str(element_definition_id)[:8]}",
                        data=validated_data,
                        attrs=element_attrs,
                    )
                    await element_data_mgr.insert(new_element_instance)

                saved_count += 1

            # Lock form instance
            await element_data_mgr.update(
                form_instance,
                locked=True
            )
        
        return {
            "form_definition_id": str(form_def._id),
            "form_instance_id": str(data.form_instance_id),
            "elements_saved": saved_count,
            "status": "submitted",
            "locked": True,
            "message": "Form submitted and locked from further editing",
        }

