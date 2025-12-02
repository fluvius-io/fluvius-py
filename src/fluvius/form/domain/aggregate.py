from fluvius.domain.aggregate import Aggregate, action
from fluvius.data import UUID_GENR, timestamp
from fluvius.error import NotFoundError, BadRequestError
from fluvius.form.element import get_element_type, ElementDataManager

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
        """Create a new document and optionally add it to one or more collections"""
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
                    attrs=data.attrs,
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
        """Copy a document with all its forms and elements"""
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
            resource_id=source_document.resource_id,
            resource_name=source_document.resource_name,
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

            # Copy forms and their elements if requested
            if data.copy_forms:
                doc_forms = await self.statemgr.query(
                    "document_form",
                    where={"document_id": source_document._id},
                    sort=(("order", "asc"),)
                )
                form_map = {}  # Map old form_id to new form_id
                
                for doc_form in doc_forms:
                    # Get the source form
                    source_form = await self.statemgr.fetch('data_form', doc_form.form_id)
                    
                    # Create new form
                    new_form_id = UUID_GENR()
                    new_form = self.init_resource(
                        "data_form",
                        _id=new_form_id,
                        form_key=f"{source_form.form_key}-copy",
                        form_name=source_form.form_name,
                        desc=source_form.desc,
                        version=source_form.version,
                        attrs=source_form.attrs,
                        owner_id=source_form.owner_id,
                        organization_id=source_form.organization_id,
                    )
                    await self.statemgr.insert(new_form)
                    form_map[source_form._id] = new_form_id
                    
                    # Copy all elements from the source form
                    elements = await self.statemgr.query(
                        "data_element",
                        where={"form_id": source_form._id},
                        sort=(("order", "asc"),)
                    )
                    for element in elements:
                        new_element = self.init_resource(
                            "data_element",
                            _id=UUID_GENR(),
                            form_id=new_form_id,
                            element_type_id=element.element_type_id,
                            element_key=element.element_key,
                            element_label=element.element_label,
                            order=element.order,
                            required=element.required,
                            attrs=element.attrs,
                            validation_rules=element.validation_rules,
                            resource_id=element.resource_id,
                            resource_name=element.resource_name,
                        )
                        await self.statemgr.insert(new_element)
                    
                    # Create document-form relationship with new form
                    new_section_id = section_map.get(doc_form.section_id) if doc_form.section_id else None
                    new_doc_form = self.init_resource(
                        "document_form",
                        _id=UUID_GENR(),
                        document_id=new_document_id,
                        section_id=new_section_id,  # Can be None if form is not in a section
                        form_id=new_form_id,
                        order=doc_form.order,
                        attrs=doc_form.attrs,
                    )
                    await self.statemgr.insert(new_doc_form)

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
                    attrs=data.attrs,
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
                attrs=data.attrs,
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
            attrs=data.attrs,
        )
        await self.statemgr.insert(doc_collection)
        
        return {
            "document_id": str(document._id),
            "collection_id": str(data.collection_id),
            "status": "added",
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
        """Save element data with validation"""
        from fluvius.data import UUID_GENR

        element = self.rootobj

        # Get element type from database
        element_type_record = await self.statemgr.fetch('element_type', element.element_type_id)

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

        # Get element data manager (reuse connector config)
        element_data_mgr = ElementDataManager()

        # Use transaction context for element data operations
        async with element_data_mgr.transaction():
            # Check if form instance exists, create if it doesn't
            form_instances = await element_data_mgr.query(
                "form_instance",
                where={"_id": data.form_instance_id},
                limit=1
            )

            if not form_instances:
                # Create form instance if it doesn't exist
                organization_id = None
                if hasattr(self, 'context') and self.context.organization_id:
                    organization_id = str(self.context.organization_id)
                form_instance = element_data_mgr.create(
                    "form_instance",
                    _id=data.form_instance_id,
                    form_id=element.form_id,
                    instance_key=f"instance-{str(data.form_instance_id)[:8]}",
                    instance_name=None,
                    locked=False,
                    attrs=data.attrs,
                    owner_id=self.context.profile_id if hasattr(self, 'context') else None,
                    organization_id=organization_id,
                )
                await element_data_mgr.insert(form_instance)
                # Refresh to get _etag from database
                form_instance = await element_data_mgr.fetch('form_instance', data.form_instance_id)
            else:
                form_instance = form_instances[0]

            # Check if element data already exists
            existing_data = await element_data_mgr.query(
                "element_data",
                where={
                    "form_instance_id": data.form_instance_id,
                    "element_id": element._id
                },
                limit=1
            )

            if existing_data:
                # Update existing element data
                element_data = existing_data[0]
                await element_data_mgr.update(
                    element_data,
                    data=validated_data,
                    attrs=data.attrs,
                    **self.audit_updated()
                )
            else:
                # Create new element data
                element_data = element_data_mgr.create(
                    "element_data",
                    _id=UUID_GENR(),
                    form_instance_id=data.form_instance_id,
                    element_id=element._id,
                    data=validated_data,
                    attrs=data.attrs,
                )
                await element_data_mgr.insert(element_data)
        
        return {
            "element_id": str(element._id),
            "form_instance_id": str(data.form_instance_id),
            "element_data_id": str(element_data._id),
            "status": "saved",
            "message": "Element data saved",
        }

    @action("form-saved", resources="data_form")
    async def save_form(self, data):
        form = self.rootobj

        # Get element data manager
        element_data_mgr = ElementDataManager()

        # Use transaction context for element data operations
        async with element_data_mgr.transaction():
            # Check if form instance exists, create if it doesn't
            form_instances = await element_data_mgr.query(
                "form_instance",
                where={"_id": data.form_instance_id},
                limit=1
            )

            if not form_instances:
                # Create form instance if it doesn't exist
                organization_id = None
                if hasattr(self, 'context') and self.context.organization_id:
                    organization_id = str(self.context.organization_id)
                form_instance = element_data_mgr.create(
                    "form_instance",
                    _id=data.form_instance_id,
                    form_id=form._id,
                    instance_key=f"instance-{str(data.form_instance_id)[:8]}",
                    instance_name=None,
                    locked=False,
                    attrs=data.attrs,
                    owner_id=self.context.profile_id if hasattr(self, 'context') else None,
                    organization_id=organization_id,
                )
                await element_data_mgr.insert(form_instance)
                # Refresh to get _etag from database
                form_instance = await element_data_mgr.fetch('form_instance', data.form_instance_id)
            else:
                form_instance = form_instances[0]

            # Save each element data
            saved_count = 0
            for element_data in data.elements:
                element_id = element_data.get("element_id")
                element_data_dict = element_data.get("data", {})
                element_attrs = element_data.get("attrs")

                if not element_id:
                    continue

                # Get element from database
                element = await self.statemgr.fetch('data_element', element_id)

                # Get element type for validation
                element_type_record = await self.statemgr.fetch('element_type', element.element_type_id)

                # Validate data
                validated_data = element_data_dict
                try:
                    element_type_cls = get_element_type(element_type_record.type_key)
                    validated_data = element_type_cls.validate_data(element_data_dict)
                except (RuntimeError, NotFoundError):
                    # Element type not registered, skip validation
                    pass

                # Check if element data already exists
                existing_data = await element_data_mgr.query(
                    "element_data",
                    where={
                        "form_instance_id": data.form_instance_id,
                        "element_id": element_id
                    },
                    limit=1
                )

                if existing_data:
                    # Update existing
                    await element_data_mgr.update(
                        existing_data[0],
                        data=validated_data,
                        attrs=element_attrs,
                        **self.audit_updated()
                    )
                else:
                    # Create new
                    new_element_data = element_data_mgr.create(
                        "element_data",
                        _id=UUID_GENR(),
                        form_instance_id=data.form_instance_id,
                        element_id=element_id,
                        data=validated_data,
                        attrs=element_attrs,
                    )
                    await element_data_mgr.insert(new_element_data)

                saved_count += 1
        
        return {
            "form_id": str(form._id),
            "form_instance_id": str(data.form_instance_id),
            "elements_saved": saved_count,
            "status": "saved",
            "message": "Form data saved (editable)",
        }

    @action("form-submitted", resources="data_form")
    async def submit_form(self, data):
        """Submit form (saves element data and locks from further editing)"""
        from fluvius.data import UUID_GENR

        form = self.rootobj

        # Get element data manager
        element_data_mgr = ElementDataManager()

        # Use transaction context for element data operations
        async with element_data_mgr.transaction():
            # Check if form instance exists, create if it doesn't
            form_instances = await element_data_mgr.query(
                "form_instance",
                where={"_id": data.form_instance_id},
                limit=1
            )

            if not form_instances:
                # Create form instance if it doesn't exist
                organization_id = None
                if hasattr(self, 'context') and self.context.organization_id:
                    organization_id = str(self.context.organization_id)
                form_instance = element_data_mgr.create(
                    "form_instance",
                    _id=data.form_instance_id,
                    form_id=form._id,
                    instance_key=f"instance-{str(data.form_instance_id)[:8]}",
                    instance_name=None,
                    locked=False,
                    attrs=data.attrs,
                    owner_id=self.context.profile_id if hasattr(self, 'context') else None,
                    organization_id=organization_id,
                )
                await element_data_mgr.insert(form_instance)
                # Refresh to get _etag from database
                form_instance = await element_data_mgr.fetch('form_instance', data.form_instance_id)
            else:
                form_instance = form_instances[0]

            # Save each element data
            saved_count = 0
            for element_data in data.elements:
                element_id = element_data.get("element_id")
                element_data_dict = element_data.get("data", {})
                element_attrs = element_data.get("attrs")

                if not element_id:
                    continue

                # Get element from database
                element = await self.statemgr.fetch('data_element', element_id)

                # Get element type for validation
                element_type_record = await self.statemgr.fetch('element_type', element.element_type_id)

                # Validate data
                validated_data = element_data_dict
                try:
                    element_type_cls = get_element_type(element_type_record.type_key)
                    validated_data = element_type_cls.validate_data(element_data_dict)
                except (RuntimeError, NotFoundError):
                    # Element type not registered, skip validation
                    pass

                # Check if element data already exists
                existing_data = await element_data_mgr.query(
                    "element_data",
                    where={
                        "form_instance_id": data.form_instance_id,
                        "element_id": element_id
                    },
                    limit=1
                )

                if existing_data:
                    # Update existing
                    await element_data_mgr.update(
                        existing_data[0],
                        data=validated_data,
                        attrs=element_attrs,
                        **self.audit_updated()
                    )
                else:
                    # Create new
                    new_element_data = element_data_mgr.create(
                        "element_data",
                        _id=UUID_GENR(),
                        form_instance_id=data.form_instance_id,
                        element_id=element_id,
                        data=validated_data,
                        attrs=element_attrs,
                    )
                    await element_data_mgr.insert(new_element_data)

                saved_count += 1

            # Lock form instance
            await element_data_mgr.update(
                form_instance,
                locked=True
            )
        
        return {
            "form_id": str(form._id),
            "form_instance_id": str(data.form_instance_id),
            "elements_saved": saved_count,
            "status": "submitted",
            "locked": True,
            "message": "Form submitted and locked from further editing",
        }

