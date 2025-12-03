from fluvius.data import UUID_TYPE, DataModel
from typing import Optional, Dict, Any, List


# ============================================================================
# TEMPLATE DEFINITION COMMANDS
# ============================================================================

# Template Commands
class CreateTemplateData(DataModel):
    """Data for creating a new document template"""
    template_key: str
    template_name: str
    collection_id: Optional[UUID_TYPE] = None  # Optional: add template to collection
    collection_ids: Optional[List[UUID_TYPE]] = None  # Optional: add template to multiple collections
    desc: Optional[str] = None
    version: Optional[int] = 1
    order: Optional[int] = None  # Optional order in collections
    owner_id: Optional[UUID_TYPE] = None
    organization_id: Optional[str] = None


class UpdateTemplateData(DataModel):
    """Data for updating template properties"""
    template_name: Optional[str] = None
    desc: Optional[str] = None
    version: Optional[int] = None
    owner_id: Optional[UUID_TYPE] = None
    organization_id: Optional[str] = None


class RemoveTemplateData(DataModel):
    """Data for removing a template"""
    pass  # Identifier is in aggroot


# Section Definition Commands
class CreateSectionDefinitionData(DataModel):
    """Data for creating a section definition within a template"""
    section_key: str
    section_name: str
    desc: Optional[str] = None
    order: Optional[int] = None


class UpdateSectionDefinitionData(DataModel):
    """Data for updating section definition properties"""
    section_name: Optional[str] = None
    desc: Optional[str] = None
    order: Optional[int] = None


class RemoveSectionDefinitionData(DataModel):
    """Data for removing a section definition"""
    pass  # Identifier is in aggroot


# Form Definition Commands
class CreateFormDefinitionData(DataModel):
    """Data for creating a form definition within a section definition"""
    form_key: str
    title: str
    desc: Optional[str] = None
    order: Optional[int] = None


class UpdateFormDefinitionData(DataModel):
    """Data for updating form definition properties"""
    title: Optional[str] = None
    desc: Optional[str] = None
    order: Optional[int] = None


class RemoveFormDefinitionData(DataModel):
    """Data for removing a form definition"""
    pass  # Identifier is in aggroot


# Element Group Definition Commands
class CreateElementGroupDefinitionData(DataModel):
    """Data for creating an element group definition within a form definition"""
    group_key: str
    group_name: Optional[str] = None
    desc: Optional[str] = None
    order: Optional[int] = None


class UpdateElementGroupDefinitionData(DataModel):
    """Data for updating element group definition properties"""
    group_name: Optional[str] = None
    desc: Optional[str] = None
    order: Optional[int] = None


class RemoveElementGroupDefinitionData(DataModel):
    """Data for removing an element group definition"""
    pass  # Identifier is in aggroot


# Element Definition Commands
class CreateElementDefinitionData(DataModel):
    """Data for creating an element definition within an element group definition"""
    element_type_id: UUID_TYPE
    element_key: str
    element_label: Optional[str] = None
    order: Optional[int] = None
    required: Optional[bool] = False
    validation_rules: Optional[Dict[str, Any]] = None
    resource_id: Optional[UUID_TYPE] = None
    resource_name: Optional[str] = None


class UpdateElementDefinitionData(DataModel):
    """Data for updating element definition properties"""
    element_label: Optional[str] = None
    order: Optional[int] = None
    required: Optional[bool] = None
    validation_rules: Optional[Dict[str, Any]] = None
    resource_id: Optional[UUID_TYPE] = None
    resource_name: Optional[str] = None


class RemoveElementDefinitionData(DataModel):
    """Data for removing an element definition"""
    pass  # Identifier is in aggroot


# ============================================================================
# DATA INSTANCE COMMANDS
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
    copy_sections: bool = True  # Copy section instances
    copy_forms: bool = True  # Copy form instances
    copy_element_groups: bool = True  # Copy element group instances
    copy_elements: bool = True  # Copy element instances
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


# Section Instance Commands
class CreateSectionInstanceData(DataModel):
    """Data for creating a section instance from a section definition"""
    section_definition_id: UUID_TYPE
    instance_key: str
    instance_name: Optional[str] = None
    order: Optional[int] = None


class UpdateSectionInstanceData(DataModel):
    """Data for updating section instance properties"""
    instance_name: Optional[str] = None
    order: Optional[int] = None


class RemoveSectionInstanceData(DataModel):
    """Data for removing a section instance"""
    pass  # Identifier is in aggroot


# Form Instance Commands
class CreateFormInstanceData(DataModel):
    """Data for creating a form instance from a form definition"""
    form_definition_id: UUID_TYPE
    instance_key: str
    instance_name: Optional[str] = None


class UpdateFormInstanceData(DataModel):
    """Data for updating form instance properties"""
    instance_name: Optional[str] = None
    attrs: Optional[Dict[str, Any]] = None


class RemoveFormInstanceData(DataModel):
    """Data for removing a form instance"""
    pass  # Identifier is in aggroot


# Element Group Instance Commands
class CreateElementGroupInstanceData(DataModel):
    """Data for creating an element group instance from an element group definition"""
    element_group_definition_id: UUID_TYPE
    instance_key: str
    instance_name: Optional[str] = None
    order: Optional[int] = None


class UpdateElementGroupInstanceData(DataModel):
    """Data for updating element group instance properties"""
    instance_name: Optional[str] = None
    order: Optional[int] = None


class RemoveElementGroupInstanceData(DataModel):
    """Data for removing an element group instance"""
    pass  # Identifier is in aggroot


# Element Instance Commands
class PopulateElementData(DataModel):
    """Data for populating an element instance with prior data"""
    element_definition_id: UUID_TYPE
    element_group_instance_id: Optional[UUID_TYPE] = None  # If provided, populate from specific element group instance


class PopulateFormData(DataModel):
    """Data for populating a form instance with prior data"""
    form_definition_id: UUID_TYPE
    form_instance_id: Optional[UUID_TYPE] = None  # If provided, populate from specific form instance
    element_definition_ids: Optional[List[UUID_TYPE]] = None  # If provided, only populate these element definitions


class SaveElementData(DataModel):
    """Data for saving element instance data"""
    element_definition_id: UUID_TYPE
    element_group_instance_id: UUID_TYPE
    instance_key: str
    data: Dict[str, Any]
    attrs: Optional[Dict[str, Any]] = None


class SaveFormData(DataModel):
    """Data for saving form instance data (multiple elements)"""
    form_definition_id: UUID_TYPE
    form_instance_id: UUID_TYPE
    elements: List[Dict[str, Any]]  # List of {element_definition_id, element_group_instance_id, instance_key, data, attrs}
    attrs: Optional[Dict[str, Any]] = None


class SubmitFormData(DataModel):
    """Data for submitting form instance (saves and locks from further editing)"""
    form_definition_id: UUID_TYPE
    form_instance_id: UUID_TYPE
    elements: List[Dict[str, Any]]  # List of {element_definition_id, element_group_instance_id, instance_key, data, attrs}
    attrs: Optional[Dict[str, Any]] = None

