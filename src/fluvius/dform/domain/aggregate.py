from fluvius.domain.aggregate import Aggregate, action
from fluvius.data import UUID_GENR, timestamp
from fluvius.error import NotFoundError, BadRequestError
from fluvius.dform.element import ElementDataManager

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
    async def create_template_section(self, data):
        """Create a section definition within a template"""
        template = self.rootobj
        section_def = self.init_resource(
            "template_section",
            _id=UUID_GENR(),
            template_id=template._id,
            section_key=data.section_key,
            section_name=data.section_name,
            desc=data.desc,
            order=data.order or 0,
        )
        await self.statemgr.insert(section_def)
        return {
            "template_section_id": str(section_def._id),
            "section_key": section_def.section_key,
            "section_name": section_def.section_name,
        }

    @action("section-definition-updated", resources="template_section")
    async def update_template_section(self, data):
        """Update section definition properties"""
        section_def = self.rootobj
        changes = data.model_dump(exclude_none=True)
        if not changes:
            raise BadRequestError("F00.001", "No changes provided for section definition update")

        await self.statemgr.update(section_def, **changes)

        updated = await self.statemgr.fetch('template_section', section_def._id)

        return {
            "template_section_id": str(updated._id),
            "section_key": updated.section_key,
            "section_name": updated.section_name,
        }

    @action("section-definition-removed", resources="template_section")
    async def remove_template_section(self, data):
        """Remove a section definition"""
        section_def = self.rootobj
        await self.statemgr.remove(section_def)
        return {
            "template_section_id": str(section_def._id),
            "status": "removed",
        }

    @action("form-definition-created", resources="template_section")
    async def create_form_definition(self, data):
        """Create a form definition and link it to the template via section"""
        section_def = self.rootobj
        form_def_id = UUID_GENR()
        
        # Create standalone form definition
        form_def = self.init_resource(
            "form_definition",
            _id=form_def_id,
            form_key=data.form_key,
            title=data.title,
            desc=data.desc,
        )
        await self.statemgr.insert(form_def)
        
        # Link form to template via TemplateForm using section_key
        template_form_def = self.init_resource(
            "template_form",
            _id=UUID_GENR(),
            template_id=section_def.template_id,
            form_id=form_def_id,
            section_key=section_def.section_key,
        )
        await self.statemgr.insert(template_form_def)
        
        return {
            "form_definition_id": str(form_def._id),
            "form_key": form_def.form_key,
            "title": form_def.title,
            "template_id": str(section_def.template_id),
            "section_key": section_def.section_key,
        }

    @action("form-definition-updated", resources="form_definition")
    async def update_form_definition(self, data):
        """Update form definition properties"""
        form_def = self.rootobj
        changes = data.model_dump(exclude_none=True)
        if not changes:
            raise BadRequestError("F00.001", "No changes provided for form definition update")

        await self.statemgr.update(form_def, **changes)

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
    async def create_form_element_group(self, data):
        """Create an element group definition within a form definition"""
        form_def = self.rootobj
        group_def = self.init_resource(
            "form_element_group",
            _id=UUID_GENR(),
            form_definition_id=form_def._id,
            group_key=data.group_key,
            group_name=data.group_name,
            desc=data.desc,
            order=data.order or 0,
        )
        await self.statemgr.insert(group_def)
        return {
            "form_element_group_id": str(group_def._id),
            "group_key": group_def.group_key,
            "group_name": group_def.group_name,
        }

    @action("element-group-definition-updated", resources="form_element_group")
    async def update_form_element_group(self, data):
        """Update element group definition properties"""
        group_def = self.rootobj
        changes = data.model_dump(exclude_none=True)
        if not changes:
            raise BadRequestError("F00.001", "No changes provided for element group definition update")

        await self.statemgr.update(group_def, **changes)

        updated = await self.statemgr.fetch('form_element_group', group_def._id)

        return {
            "form_element_group_id": str(updated._id),
            "group_key": updated.group_key,
            "group_name": updated.group_name,
        }

    @action("element-group-definition-removed", resources="form_element_group")
    async def remove_form_element_group(self, data):
        """Remove an element group definition"""
        group_def = self.rootobj
        await self.statemgr.remove(group_def)
        return {
            "form_element_group_id": str(group_def._id),
            "status": "removed",
        }

    @action("element-definition-created")
    async def create_element_definition(self, data):
        """Create an element definition"""
        element_def = self.init_resource(
            "element_definition",
            _id=self.aggroot.identifier,
            element_key=data.element_key,
            element_label=data.element_label,
            element_schema=data.element_schema,
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
        """Create a new document instance from a template and copy all structure"""
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
        
        # Copy structure from template:
        # 1. template_section -> document_section
        # 2. template_form + form_definition -> form (FormInstance)
        # 3. form_element -> element (ElementInstance)
        # 4. form_element + element_definition -> element (ElementInstance)
        
        # 1. Create document sections from template sections
        template_sections = await self.statemgr.query(
            "template_section",
            where={"template_id": data.template_id},
            sort=(("order", "asc"),)
        )
        
        for section_def in template_sections:
            section = self.init_resource(
                "document_section",
                _id=UUID_GENR(),
                document_id=document._id,
                section_key=section_def.section_key,
                section_name=section_def.section_name,
                desc=section_def.desc,
                order=section_def.order,
            )
            await self.statemgr.insert(section)
        
        # 2. Create form instances from template_form + form_definition
        template_forms = await self.statemgr.query(
            "template_form",
            where={"template_id": data.template_id}
        )
        
        # Track form_id -> form_instance_id mapping for element creation
        form_instance_map = {}  # form_definition_id -> form_instance_id
        
        for tpl_form in template_forms:
            form_def = await self.statemgr.fetch('form_definition', tpl_form.form_id)
            if not form_def:
                continue
            
            form_instance_id = UUID_GENR()
            form_instance = self.init_resource(
                "document_form",
                _id=form_instance_id,
                document_id=document._id,
                form_key=form_def.form_key,
                section_key=tpl_form.section_key,
                title=form_def.title,
                desc=form_def.desc,
                order=0,
                locked=False,
            )
            await self.statemgr.insert(form_instance)
            form_instance_map[form_def._id] = form_instance_id
            
            # 3. Create element group instances from form_element_group
            element_groups = await self.statemgr.query(
                "form_element_group",
                where={"form_definition_id": form_def._id},
                sort=(("order", "asc"),)
            )
            
            for group_def in element_groups:
                element_group = self.init_resource(
                    "element_group",
                    _id=UUID_GENR(),
                    form_id=form_instance_id,
                    group_key=group_def.group_key,
                    title=group_def.group_name or group_def.group_key,
                    desc=group_def.desc,
                    order=group_def.order,
                )
                await self.statemgr.insert(element_group)
            
            # 4. Create element instances from form_element + element_definition
            form_elements = await self.statemgr.query(
                "form_element",
                where={"form_definition_id": form_def._id},
                sort=(("order", "asc"),)
            )
            
            for form_elem in form_elements:
                # Get the element definition to retrieve the schema
                elem_def = await self.statemgr.query(
                    "element_definition",
                    where={"element_key": form_elem.element_key},
                    limit=1
                )
                
                element = self.init_resource(
                    "element",
                    _id=UUID_GENR(),
                    document_id=document._id,
                    form_id=form_instance_id,
                    group_key=form_elem.group_key,
                    element_key=form_elem.element_key,
                    data={},  # Initialize with empty data
                )
                await self.statemgr.insert(element)
        
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
        
        return document

    @action("document-updated", resources="document")
    async def update_document(self, data):
        """Update document properties"""
        document = self.rootobj
        changes = data.model_dump(exclude_none=True)
        if not changes:
            raise BadRequestError("F00.002", "No changes provided for document update")

        await self.statemgr.update(document, **changes)

        # Refresh the object to get updated values
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
            sections = await self.statemgr.query(
                "document_section",
                where={"document_id": source_document._id},
                sort=(("order", "asc"),)
            )
            section_map = {}
            for section in sections:
                new_section_id = UUID_GENR()
                new_section = self.init_resource(
                    "document_section",
                    _id=new_section_id,
                    document_id=new_document_id,
                    section_key=section.section_key,
                    section_name=section.section_name,
                    desc=section.desc,
                    order=section.order,
                )
                await self.statemgr.insert(new_section)
                section_map[section._id] = new_section_id

            # Copy form instances if requested
            if data.copy_forms:
                for old_section_id, new_section_id in section_map.items():
                    async with element_data_mgr.transaction():
                        forms = await element_data_mgr.query(
                            "document_form",
                            where={"section_id": old_section_id},
                        )
                        form_map = {}
                        
                        for form in forms:
                            new_form_id = UUID_GENR()
                            new_form = element_data_mgr.create(
                                "document_form",
                                _id=new_form_id,
                                section_id=new_section_id,
                                form_definition_id=form.form_definition_id,
                                instance_key=form.instance_key,
                                instance_name=form.instance_name,
                                locked=False,  # New instance is not locked
                                attrs=form.attrs,
                                owner_id=form.owner_id,
                                organization_id=form.organization_id,
                            )
                            await element_data_mgr.insert(new_form)
                            form_map[form._id] = new_form_id
                            
                            # Copy element group instances if requested
                            if data.copy_element_groups:
                                element_groups = await element_data_mgr.query(
                                    "element_group",
                                    where={"form_id": form._id},
                                )
                                element_group_map = {}
                                
                                for group_instance in element_groups:
                                    new_group_instance_id = UUID_GENR()
                                    new_group_instance = element_data_mgr.create(
                                        "element_group",
                                        _id=new_group_instance_id,
                                        form_id=new_form_id,
                                        form_element_group_id=group_instance.form_element_group_id,
                                        instance_key=group_instance.instance_key,
                                        instance_name=group_instance.instance_name,
                                        order=group_instance.order,
                                    )
                                    await element_data_mgr.insert(new_group_instance)
                                    element_group_map[group_instance._id] = new_group_instance_id
                                    
                                    # Copy element instances if requested
                                    if data.copy_elements:
                                        elements = await element_data_mgr.query(
                                            "element",
                                            where={"element_group_id": group_instance._id},
                                        )
                                        
                                        for element in elements:
                                            new_element = element_data_mgr.create(
                                                "element",
                                                _id=UUID_GENR(),
                                                element_group_id=new_group_instance_id,
                                                element_definition_id=element.element_definition_id,
                                                instance_key=element.instance_key,
                                                data=element.data,
                                                attrs=element.attrs,
                                            )
                                            await element_data_mgr.insert(new_element)

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
            "element_group_id": str(data.element_group_id) if data.element_group_id else None,
            "status": "populated",
            "data": None,
        }
        
        if data.element_group_id:
            async with element_data_mgr.transaction():
                # Find existing element instance data
                elements = await element_data_mgr.query(
                    "element",
                    where={
                        "element_group_id": data.element_group_id,
                        "element_definition_id": element_def._id
                    },
                    limit=1
                )
                if elements:
                    result["data"] = elements[0].data
        
        return result

    @action("form-populated", resources="form_definition")
    async def populate_form(self, data):
        """Populate form with prior data from a form instance"""
        form_def = self.rootobj
        
        element_data_mgr = ElementDataManager()
        
        result = {
            "form_definition_id": str(form_def._id),
            "form_id": str(data.form_id) if data.form_id else None,
            "element_definition_ids": [str(eid) for eid in data.element_definition_ids] if data.element_definition_ids else None,
            "status": "populated",
            "elements": [],
        }
        
        if data.form_id:
            async with element_data_mgr.transaction():
                # Get all element group instances for this form instance
                element_groups = await element_data_mgr.query(
                    "element_group",
                    where={"form_id": data.form_id}
                )
                
                for group_instance in element_groups:
                    # Get all element instances for this group
                    elements = await element_data_mgr.query(
                        "element",
                        where={"element_group_id": group_instance._id}
                    )
                    
                    for element in elements:
                        # Filter by element_definition_ids if provided
                        if data.element_definition_ids and element.element_definition_id not in data.element_definition_ids:
                            continue
                        
                        result["elements"].append({
                            "element_definition_id": str(element.element_definition_id),
                            "element_group_id": str(group_instance._id),
                            "instance_key": element.instance_key,
                            "data": element.data,
                        })
        
        return result

    @action("element-saved", resources="document_form")
    async def save_element(self, data):
        """Save element data within a document form
        
        Data format: {"data": {"<element_key>": {<element_data>}}}
        """
        document_form = self.rootobj
        
        saved_elements = []
        
        # Process each element in the data
        for element_key, element_data in data.data.items():
            # Find the element instance for this form and element_key
            existing_elements = await self.statemgr.query(
                "element",
                where={
                    "form_id": document_form._id,
                    "element_key": element_key,
                },
                limit=1
            )
            
            if existing_elements:
                # Update existing element instance
                element = existing_elements[0]
                await self.statemgr.update(
                    element,
                    data=element_data,
                    **self.audit_updated()
                )
                saved_elements.append({
                    "element_key": element_key,
                    "element_id": str(element._id),
                    "status": "updated",
                })
            else:
                # Element instance doesn't exist - this shouldn't happen if document was created properly
                # but we can create it if needed
                element = self.init_resource(
                    "element",
                    _id=UUID_GENR(),
                    document_id=document_form.document_id,
                    form_id=document_form._id,
                    group_key="",  # Would need to look up from form_element
                    element_key=element_key,
                    data=element_data,
                )
                await self.statemgr.insert(element)
                saved_elements.append({
                    "element_key": element_key,
                    "element_id": str(element._id),
                    "status": "created",
                })
        
        return {
            "document_form_id": str(document_form._id),
            "form_key": document_form.form_key,
            "elements": saved_elements,
            "status": "saved",
        }

    @action("form-saved", resources="document_form")
    async def save_form(self, data):
        """Save form data (multiple elements) but still allow further editing"""
        document_form = self.rootobj
        
        saved_elements = []
        
        # Process each element in the data
        for element_key, element_data in data.data.items():
            # Find the element instance for this form and element_key
            existing_elements = await self.statemgr.query(
                "element",
                where={
                    "form_id": document_form._id,
                    "element_key": element_key,
                },
                limit=1
            )
            
            if existing_elements:
                # Update existing element instance
                element = existing_elements[0]
                await self.statemgr.update(
                    element,
                    data=element_data,
                    **self.audit_updated()
                )
                saved_elements.append({
                    "element_key": element_key,
                    "element_id": str(element._id),
                    "status": "updated",
                })
            else:
                # Element instance doesn't exist - create it
                element = self.init_resource(
                    "element",
                    _id=UUID_GENR(),
                    document_id=document_form.document_id,
                    form_id=document_form._id,
                    group_key="",
                    element_key=element_key,
                    data=element_data,
                )
                await self.statemgr.insert(element)
                saved_elements.append({
                    "element_key": element_key,
                    "element_id": str(element._id),
                    "status": "created",
                })
        
        return {
            "document_form_id": str(document_form._id),
            "form_key": document_form.form_key,
            "elements": saved_elements,
            "status": "saved",
        }

    @action("form-submitted", resources="document_form")
    async def submit_form(self, data):
        """Submit form (saves element data and locks from further editing)"""
        document_form = self.rootobj
        
        # Check if form is already locked
        if document_form.locked:
            raise BadRequestError(
                "F00.207",
                f"Form is already locked and cannot be modified: {document_form._id}"
            )
        
        saved_elements = []
        
        # Process each element in the data
        for element_key, element_data in data.data.items():
            # Find the element instance for this form and element_key
            existing_elements = await self.statemgr.query(
                "element",
                where={
                    "form_id": document_form._id,
                    "element_key": element_key,
                },
                limit=1
            )
            
            if existing_elements:
                # Update existing element instance
                element = existing_elements[0]
                await self.statemgr.update(
                    element,
                    data=element_data,
                    **self.audit_updated()
                )
                saved_elements.append({
                    "element_key": element_key,
                    "element_id": str(element._id),
                    "status": "updated",
                })
            else:
                # Element instance doesn't exist - create it
                element = self.init_resource(
                    "element",
                    _id=UUID_GENR(),
                    document_id=document_form.document_id,
                    form_id=document_form._id,
                    group_key="",
                    element_key=element_key,
                    data=element_data,
                )
                await self.statemgr.insert(element)
                saved_elements.append({
                    "element_key": element_key,
                    "element_id": str(element._id),
                    "status": "created",
                })
        
        # Lock the form
        await self.statemgr.update(
            document_form,
            locked=True,
            **self.audit_updated()
        )
        
        return {
            "document_form_id": str(document_form._id),
            "form_key": document_form.form_key,
            "elements": saved_elements,
            "status": "submitted",
            "locked": True,
        }

