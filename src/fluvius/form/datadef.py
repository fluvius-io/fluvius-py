from fluvius.data import UUID_TYPE, DataModel
from typing import Optional, Dict, Any, List


# Collection Commands
class CreateCollectionData(DataModel):
    """Data for creating a new collection"""
    collection_key: str
    collection_name: str
    desc: Optional[str] = None
    attrs: Optional[Dict[str, Any]] = None
    owner_id: Optional[UUID_TYPE] = None
    organization_id: Optional[str] = None


class UpdateCollectionData(DataModel):
    """Data for updating collection properties"""
    collection_name: Optional[str] = None
    desc: Optional[str] = None
    attrs: Optional[Dict[str, Any]] = None
    owner_id: Optional[UUID_TYPE] = None
    organization_id: Optional[str] = None


class RemoveCollectionData(DataModel):
    """Data for removing a collection"""
    pass  # Identifier is in aggroot


# Document Commands
class CreateDocumentData(DataModel):
    """Data for creating a new document"""
    document_key: str
    document_name: str
    desc: Optional[str] = None
    version: Optional[int] = 1
    attrs: Optional[Dict[str, Any]] = None
    owner_id: Optional[UUID_TYPE] = None
    organization_id: Optional[str] = None
    resource_id: Optional[UUID_TYPE] = None
    resource_name: Optional[str] = None


class UpdateDocumentData(DataModel):
    """Data for updating document properties"""
    document_name: Optional[str] = None
    desc: Optional[str] = None
    version: Optional[int] = None
    attrs: Optional[Dict[str, Any]] = None
    owner_id: Optional[UUID_TYPE] = None
    organization_id: Optional[str] = None
    resource_id: Optional[UUID_TYPE] = None
    resource_name: Optional[str] = None


class RemoveDocumentData(DataModel):
    """Data for removing a document"""
    pass  # Identifier is in aggroot


class CopyDocumentData(DataModel):
    """Data for copying a document"""
    new_document_key: str
    new_document_name: Optional[str] = None
    copy_forms: bool = True
    copy_sections: bool = True
    attrs: Optional[Dict[str, Any]] = None


# Form Data Commands
class PopulateElementData(DataModel):
    """Data for populating an element with prior data"""
    element_id: UUID_TYPE
    form_instance_id: Optional[UUID_TYPE] = None  # If provided, populate from specific form instance


class PopulateFormData(DataModel):
    """Data for populating a form with prior data"""
    form_id: UUID_TYPE
    form_instance_id: Optional[UUID_TYPE] = None  # If provided, populate from specific form instance
    element_ids: Optional[List[UUID_TYPE]] = None  # If provided, only populate these elements


class SaveElementData(DataModel):
    """Data for saving element data"""
    element_id: UUID_TYPE
    form_instance_id: UUID_TYPE
    data: Dict[str, Any]
    attrs: Optional[Dict[str, Any]] = None


class SaveFormData(DataModel):
    """Data for saving form data (multiple elements)"""
    form_id: UUID_TYPE
    form_instance_id: UUID_TYPE
    elements: List[Dict[str, Any]]  # List of {element_id, data, attrs}
    attrs: Optional[Dict[str, Any]] = None


class SubmitFormData(DataModel):
    """Data for submitting form (saves and locks from further editing)"""
    form_id: UUID_TYPE
    form_instance_id: UUID_TYPE
    elements: List[Dict[str, Any]]  # List of {element_id, data, attrs}
    attrs: Optional[Dict[str, Any]] = None

