from fluvius.data import UUID_TYPE, DataModel
from typing import Optional, Dict, Any, List


# ============================================================================
# DATA INSTANCE COMMANDS
# Note: Registry tables (TemplateRegistry, FormRegistry, ElementRegistry) are
# populated by developers directly, not through domain commands.
# ============================================================================

# Collection Commands
class CreateCollectionData(DataModel):
    """Data for creating a new collection"""
    collection_key: str
    collection_name: str
    desc: Optional[str] = None
    owner_id: Optional[UUID_TYPE] = None
    organization_id: Optional[str] = None


class UpdateCollectionData(DataModel):
    """Data for updating collection properties"""
    collection_name: Optional[str] = None
    desc: Optional[str] = None
    owner_id: Optional[UUID_TYPE] = None
    organization_id: Optional[str] = None


class RemoveCollectionData(DataModel):
    """Data for removing a collection"""
    pass  # Identifier is in aggroot


# Document Commands
class CreateDocumentData(DataModel):
    """Data for creating a new document instance from a template"""
    template_id: UUID_TYPE  # Required: template to create document from
    document_key: str
    document_name: str
    collection_id: Optional[UUID_TYPE] = None  # Optional: single collection to add document to
    collection_ids: Optional[List[UUID_TYPE]] = None  # Optional: multiple collections to add document to
    desc: Optional[str] = None
    version: Optional[int] = 1
    order: Optional[int] = None  # Optional order in collections
    owner_id: Optional[UUID_TYPE] = None
    organization_id: Optional[str] = None
    resource_id: Optional[UUID_TYPE] = None
    resource_name: Optional[str] = None


class UpdateDocumentData(DataModel):
    """Data for updating document properties"""
    document_name: Optional[str] = None
    desc: Optional[str] = None
    version: Optional[int] = None
    owner_id: Optional[UUID_TYPE] = None
    organization_id: Optional[str] = None
    resource_id: Optional[UUID_TYPE] = None
    resource_name: Optional[str] = None


class RemoveDocumentData(DataModel):
    """Data for removing a document"""
    pass  # Identifier is in aggroot


class CopyDocumentData(DataModel):
    """Data for copying a document instance"""
    new_document_key: str
    new_document_name: Optional[str] = None
    copy_nodes: bool = True  # Copy document nodes
    copy_form_submissions: bool = True  # Copy form submissions
    copy_form_elements: bool = True  # Copy form elements
    target_collection_id: Optional[UUID_TYPE] = None  # Optional: add copied document to this collection
    order: Optional[int] = None  # Optional order in target collection


class MoveDocumentData(DataModel):
    """Data for moving a document between collections"""
    target_collection_id: UUID_TYPE
    source_collection_id: Optional[UUID_TYPE] = None  # If None, remove from any collection
    order: Optional[int] = None  # Optional order in target collection


class AddDocumentToCollectionData(DataModel):
    """Data for adding a document to additional collections"""
    collection_id: UUID_TYPE  # Collection to add document to
    order: Optional[int] = None  # Optional order in collection


# Document Node Commands
class CreateDocumentNodeData(DataModel):
    """Data for creating a document node (section/content)"""
    node_key: str
    section_name: str
    parent_node: Optional[UUID_TYPE] = None  # Parent node ID for nesting
    desc: Optional[str] = None
    order: Optional[int] = None


class UpdateDocumentNodeData(DataModel):
    """Data for updating document node properties"""
    section_name: Optional[str] = None
    desc: Optional[str] = None
    order: Optional[int] = None


class RemoveDocumentNodeData(DataModel):
    """Data for removing a document node"""
    pass  # Identifier is in aggroot


# ============================================================================
# FORM COMMANDS (aggroot = form_submission for Update/Remove/Submit)
# ============================================================================

class InitializeFormData(DataModel):
    """
    Data for creating and initializing a form submission.
    
    This command:
    - Creates a new form submission from a form registry entry
    - Sets up the form elements based on form registry definition
    - Optionally populates elements with prior data from another form submission
    
    aggroot: document (creates new form_submission)
    """
    # Form creation fields
    form_registry_id: UUID_TYPE  # Reference to form in registry
    form_key: str
    section_key: str
    title: str
    desc: Optional[str] = None
    order: Optional[int] = None
    # Initialization options
    source_submission_id: Optional[UUID_TYPE] = None  # Populate from prior submission
    element_keys: Optional[List[str]] = None  # Only initialize these elements (None = all)
    initial_data: Optional[Dict[str, Dict[str, Any]]] = None  # {"element_key": {data}}


class UpdateFormData(DataModel):
    """Data for updating form properties"""
    title: Optional[str] = None
    desc: Optional[str] = None
    order: Optional[int] = None
    status: Optional[str] = None  # "draft", "submitted", etc.


class RemoveFormData(DataModel):
    """Data for removing a form"""
    pass  # Identifier is in aggroot


class SubmitFormData(DataModel):
    """
    Data for submitting/saving form data.
    
    This command:
    - Updates existing element data
    - Creates new elements if they don't exist
    - Removes elements not in the payload (if replace=True)
    - Validates required elements (if validate=True)
    - Sets form status (default "submitted", use "draft" for save without submit)
    
    aggroot: form_submission
    """
    payload: Dict[str, Dict[str, Any]]  # {"element_key": {data}, ...}
    replace: bool = False  # Remove elements not in the payload
    validate: bool = True  # Validate required elements before submitting
    status: str = "submitted"  # "draft", "submitted", etc.
