from fluvius.domain.aggregate import Aggregate, action
from fluvius.data import UUID_GENR
from fluvius.error import NotFoundError, BadRequestError
from fluvius.dform.document import DocumentTemplateRegistry, DocumentSection, FormNode, ContentNode
from fluvius.data import UUID_TYPE

from .. import logger


class FormAggregate(Aggregate):
    """Aggregate for form domain operations
    
    Note: Registry tables (TemplateRegistry, FormRegistry, ElementRegistry) are
    populated by developers directly, not through domain commands.
    """

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
    
    async def _create_document_nodes(self, document_id: UUID_TYPE, nodes: list, parent_id: UUID_TYPE):
        for index, node_def in enumerate(nodes):
            node_type = None
            ctype = None
            form_key = None
            attrs = {}
            content = getattr(node_def, 'content', None)
            title = getattr(node_def, 'title', None)
            
            if isinstance(node_def, DocumentSection):
                node_type = "section"
            
            if isinstance(node_def, ContentNode):
                node_type = "content"
                ctype = node_def.ctype
            
            if isinstance(node_def, FormNode):
                node_type = 'form'
                form_key = node_def.form_key
                attrs = node_def.attrs
            
            node_id = UUID_GENR()
            node_resource = self.init_resource(
                "document_node",
                _id=node_id,
                document_id=document_id,
                parent_node=parent_id,
                node_key=str(UUID_GENR()),
                node_type=node_type,
                order=index,
                title=title,
                content=content,
                ctype=ctype,
                form_key=form_key,
                attrs=attrs
            )
            await self.statemgr.insert(node_resource)
            
            if isinstance(node_def, DocumentSection) and node_def.children:
                await self._create_document_nodes(document_id, node_def.children, node_id)

    @action("document-created")
    async def create_document(self, data):
        """Create a new document instance from a template"""
        # Verify template exists in registry
        template = await self.statemgr.fetch('template_registry', data.template_id)
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

        template_def = DocumentTemplateRegistry.get(template.template_key)
        if template_def and template_def.children:
            await self._create_document_nodes(
                document_id=document._id,
                nodes=template_def.children,
                parent_id=None
            )
            
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
        """Copy a document with all its nodes, form submissions, and form elements"""
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

        # Copy document nodes if requested
        if data.copy_nodes:
            nodes = await self.statemgr.query(
                "document_node",
                where={"document_id": source_document._id},
                sort=(("order", "asc"),)
            )
            node_map = {}  # old_id -> new_id for parent references
            for node in nodes:
                new_node_id = UUID_GENR()
                new_node = self.init_resource(
                    "document_node",
                    _id=new_node_id,
                    document_id=new_document_id,
                    parent_node=node_map.get(node.parent_node) if node.parent_node else None,
                    node_key=node.node_key,
                    node_type=node.node_type,
                    order=node.order,
                    # Common fields
                    title=node.title,
                    desc=node.desc,
                    # Content node fields
                    content=node.content,
                    ctype=node.ctype,
                    # Form node fields
                    form_key=node.form_key,
                    # Extensible attributes
                    attrs=node.attrs,
                )
                await self.statemgr.insert(new_node)
                node_map[node._id] = new_node_id

        # Copy form submissions if requested
        if data.copy_form_submissions:
            forms = await self.statemgr.query(
                "form_submission",
                where={"document_id": source_document._id},
                sort=(("order", "asc"),)
            )
            form_map = {}  # old_id -> new_id
            
            for form in forms:
                new_form_id = UUID_GENR()
                new_form = self.init_resource(
                    "form_submission",
                    _id=new_form_id,
                    document_id=new_document_id,
                    form_key=form.form_key,
                    title=form.title,
                    desc=form.desc,
                    order=form.order,
                    locked=False,  # New copy is not locked
                    status="draft",  # New copy starts as draft
                )
                await self.statemgr.insert(new_form)
                form_map[form._id] = new_form_id
                
                # Copy form elements if requested
                if data.copy_form_elements:
                    elements = await self.statemgr.query(
                        "form_element",
                        where={"form_submission_id": form._id},
                    )
                    
                    for element in elements:
                        new_element = self.init_resource(
                            "form_element",
                            _id=UUID_GENR(),
                            form_submission_id=new_form_id,
                            element_registry_id=element.element_registry_id,
                            element_name=element.element_name,
                            index=element.index,
                            required=element.required,
                            data=element.data,
                            status="draft",  # New copy starts as draft
                        )
                        await self.statemgr.insert(new_element)

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

    # ============================================================================
    # DOCUMENT NODE METHODS
    # ============================================================================

    @action("document-node-created", resources="document")
    async def create_document_node(self, data):
        """
        Create a document node.
        
        Supports different node types:
        - "section": Container node with children
        - "content": Text/header/graphic content
        - "form": Form reference
        """
        document = self.rootobj
        
        # Verify parent node exists if specified
        if data.parent_node:
            parent = await self.statemgr.fetch('document_node', data.parent_node)
            if not parent:
                raise NotFoundError(
                    "F00.206",
                    f"Parent node not found: {data.parent_node}",
                    None
                )
            if parent.document_id != document._id:
                raise BadRequestError(
                    "F00.208",
                    f"Parent node belongs to different document",
                    None
                )
        
        # Determine order if not specified
        order = data.order
        if order is None:
            max_order = await self.statemgr.query(
                "document_node",
                where={"document_id": document._id, "parent_node": data.parent_node},
                sort=(("order", "desc"),),
                limit=1
            )
            order = (max_order[0].order + 1) if max_order else 0
        
        node = self.init_resource(
            "document_node",
            _id=UUID_GENR(),
            document_id=document._id,
            parent_node=data.parent_node,
            node_key=data.node_key,
            node_type=data.node_type,
            order=order,
            # Common fields
            title=data.title,
            desc=data.desc,
            # Content node fields
            content=data.content,
            ctype=data.ctype,
            # Form node fields
            form_key=data.form_key,
            # Extensible attributes
            attrs=data.attrs,
        )
        await self.statemgr.insert(node)
        
        return {
            "document_node_id": str(node._id),
            "document_id": str(document._id),
            "node_key": node.node_key,
            "node_type": node.node_type,
            "title": node.title,
        }

    @action("document-node-updated", resources="document_node")
    async def update_document_node(self, data):
        """Update document node properties"""
        node = self.rootobj
        changes = data.model_dump(exclude_none=True)
        if not changes:
            raise BadRequestError("F00.001", "No changes provided for document node update")

        await self.statemgr.update(node, **changes)
        updated = await self.statemgr.fetch('document_node', node._id)

        return {
            "document_node_id": str(updated._id),
            "node_key": updated.node_key,
            "node_type": updated.node_type,
            "title": updated.title,
        }

    @action("document-node-removed", resources="document_node")
    async def remove_document_node(self, data):
        """Remove a document node"""
        node = self.rootobj
        await self.statemgr.remove(node)
        return {
            "document_node_id": str(node._id),
            "status": "removed",
        }

    # ============================================================================
    # FORM METHODS
    # ============================================================================

    @action("form-initialized", resources="document")
    async def initialize_form(self, data):
        """Create and initialize a form submission with element structure"""
        document = self.rootobj
        
        # Verify form registry entry exists
        form_registry = await self.statemgr.exist('form_registry', where={"form_key": data.form_key})
        if not form_registry:
            raise NotFoundError(
                "F00.209",
                f"Form registry entry not found: {data.form_key}",
                None
            )
        
        # Check if form with same key already exists in document
        existing = await self.statemgr.query(
            "form_submission",
            where={"document_id": document._id, "form_reg_id": form_registry._id},
            limit=1
        )
        if existing:
            raise BadRequestError(
                "F00.210",
                f"Form with key '{data.form_key}' already exists in document",
                None
            )
        
        # Determine order if not specified
        order = data.order
        if order is None:
            max_order = await self.statemgr.query(
                "form_submission",
                where={"document_id": document._id},
                sort=(("order", "desc"),),
                limit=1
            )
            order = (max_order[0].order + 1) if max_order else 0
        # raise ValueError(data)
        # Create form submission
        form_submission_id = data.form_submission_id if data.form_submission_id else UUID_GENR()
        form_submission = self.init_resource(
            "form_submission",
            _id=form_submission_id,
            document_id=document._id,
            form_reg_id=form_registry._id,
            title=data.title,
            desc=data.desc,
            order=order,
            locked=False,
            status="draft",
        )
        await self.statemgr.insert(form_submission)
        
        created_elements = []
        
        # Initialize with data from source submission if specified
        if data.source_submission_id:
            source_elements = await self.statemgr.query(
                "form_element",
                where={"form_submission_id": data.source_submission_id}
            )
            
            for src_elem in source_elements:
                # Filter by element_keys if specified
                if data.element_keys and src_elem.element_name not in data.element_keys:
                    continue
                
                new_elem = self.init_resource(
                    "form_element",
                    _id=UUID_GENR(),
                    form_submission_id=form_submission_id,
                    element_registry_id=src_elem.element_registry_id,
                    element_name=src_elem.element_name,
                    index=src_elem.index,
                    required=src_elem.required,
                    data=src_elem.data,
                    status="draft",
                )
                await self.statemgr.insert(new_elem)
                created_elements.append({
                    "element_name": new_elem.element_name,
                    "element_id": str(new_elem._id),
                })
        
        # Initialize with provided initial_data
        if data.initial_data:
            for element_key, element_data in data.initial_data.items():
                # Check if element already exists (from source)
                existing_elem = await self.statemgr.query(
                    "form_element",
                    where={"form_submission_id": form_submission_id, "element_name": element_key},
                    limit=1
                )
                
                if existing_elem:
                    # Update existing element
                    await self.statemgr.update(existing_elem[0], data=element_data)
                else:
                    # Look up element in registry by key
                    elem_registry = await self.statemgr.query(
                        "element_registry",
                        where={"element_key": element_key},
                        limit=1
                    )
                    
                    if elem_registry:
                        new_elem = self.init_resource(
                            "form_element",
                            _id=UUID_GENR(),
                            form_submission_id=form_submission_id,
                            element_registry_id=elem_registry[0]._id,
                            element_name=element_key,
                            index=0,
                            required=False,
                            data=element_data,
                            status="draft",
                        )
                        await self.statemgr.insert(new_elem)
                        created_elements.append({
                            "element_name": new_elem.element_name,
                            "element_id": str(new_elem._id),
                        })
        
        return {
            "form_submission_id": str(form_submission_id),
            "document_id": str(document._id),
            # "form_key": form_submission.form_key,
            "form_reg_id": form_submission.form_reg_id,
            "title": form_submission.title,
            "elements": created_elements,
            "status": "initialized",
        }

    @action("form-updated", resources="form_submission")
    async def update_form(self, data):
        """Update form submission properties"""
        form_submission = self.rootobj
        changes = data.model_dump(exclude_none=True)
        if not changes:
            raise BadRequestError("F00.001", "No changes provided for form update")

        await self.statemgr.update(form_submission, **changes)
        updated = await self.statemgr.fetch('form_submission', form_submission._id)

        return {
            "form_submission_id": str(updated._id),
            "form_key": updated.form_key,
            "title": updated.title,
            "status": updated.status,
        }

    @action("form-removed", resources="form_submission")
    async def remove_form(self, data):
        """Remove a form submission"""
        form_submission = self.rootobj
        await self.statemgr.remove(form_submission)
        return {
            "form_submission_id": str(form_submission._id),
            "status": "removed",
        }

    @action("form-submitted", resources="form_submission")
    async def submit_form(self, data):
        """Submit/save form data"""
        form_submission = self.rootobj
        
        # Check if form is locked and status is not draft
        if form_submission.locked and form_submission.status != "draft":
            raise BadRequestError(
                "F00.207",
                f"Form is locked and cannot be modified: {form_submission._id}"
            )
        
        processed_elements = []
        existing_element_names = set()
        
        # Process each element in the payload
        for element_name, element_data in data.payload.items():
            existing_element_names.add(element_name)
            
            # Find existing element
            existing_elements = await self.statemgr.query(
                "form_element",
                where={
                    "form_id": form_submission._id,
                    "elem_name": element_name,
                },
                limit=1
            )
            
            if existing_elements:
                # Update existing element
                element = existing_elements[0]
                await self.statemgr.update(
                    element,
                    data=element_data,
                    status=data.status,
                )
                processed_elements.append({
                    "element_name": element_name,
                    "element_id": str(element._id),
                    "action": "updated",
                })
            else:
                # Create new element - look up in registry
                elem_registry = await self.statemgr.query(
                    "element_registry",
                    where={"element_key": element_name},
                    limit=1
                )
                
                if elem_registry:
                    element = self.init_resource(
                        "form_element",
                        _id=UUID_GENR(),
                        form_id=form_submission._id,
                        elem_reg_id=elem_registry[0]._id,
                        elem_name=element_name,
                        index=0,
                        required=False,
                        data=element_data,
                        status=data.status,
                    )
                    await self.statemgr.insert(element)
                    processed_elements.append({
                        "element_name": element_name,
                        "element_id": str(element._id),
                        "action": "created",
                    })
        
        # Remove elements not in payload if replace=True
        if data.replace:
            all_elements = await self.statemgr.query(
                "form_element",
                where={"form_submission_id": form_submission._id}
            )
            for elem in all_elements:
                if elem.element_name not in existing_element_names:
                    await self.statemgr.remove(elem)
                    processed_elements.append({
                        "element_name": elem.element_name,
                        "element_id": str(elem._id),
                        "action": "removed",
                    })
        
        # Update form submission status
        should_lock = data.status == "submitted"
        await self.statemgr.update(
            form_submission,
            status=data.status,
            locked=should_lock,
        )
        
        return {
            "document_id": str(form_submission.document_id),
            "form_submission_id": str(form_submission._id),
            "elements": processed_elements,
            "status": data.status,
            "locked": should_lock,
        }
