from fluvius.query import DomainQueryManager, DomainQueryResource
from fluvius.query.field import StringField, UUIDField, DatetimeField, IntegerField, BooleanField, ListField, DictField, PrimaryID
from fluvius.data import UUID_TYPE, DataModel

from .domain.domain import FormDomain
from .model import FormDataManager


class CollectionScope(DataModel):
    __default_key__ = 'collection_id'
    collection_id: UUID_TYPE


class DocumentScope(DataModel):
    __default_key__ = 'document_id'
    document_id: UUID_TYPE


class FormScope(DataModel):
    __default_key__ = 'form_id'
    form_id: UUID_TYPE


class FormQueryManager(DomainQueryManager):
    """Query manager for form domain"""
    __data_manager__ = FormDataManager

    class Meta(DomainQueryManager.Meta):
        prefix = FormDomain.Meta.prefix
        tags = FormDomain.Meta.tags


resource = FormQueryManager.register_resource


@resource('collection')
class CollectionQuery(DomainQueryResource):
    """Query collections"""

    class Meta(DomainQueryResource.Meta):
        description = "List and search collections"
        backend_model = "collection"

    id: UUID_TYPE = PrimaryID("Collection ID")
    collection_key: str = StringField("Collection Key")
    collection_name: str = StringField("Collection Name")
    desc: str = StringField("Description")
    owner_id: UUID_TYPE = UUIDField("Owner ID")
    organization_id: str = StringField("Organization ID")


@resource('document')
class DocumentQuery(DomainQueryResource):
    """Query documents"""

    class Meta(DomainQueryResource.Meta):
        description = "List and search documents"
        backend_model = "document"

    id: UUID_TYPE = PrimaryID("Document ID")
    document_key: str = StringField("Document Key")
    document_name: str = StringField("Document Name")
    desc: str = StringField("Description")
    version: int = IntegerField("Version")
    owner_id: UUID_TYPE = UUIDField("Owner ID")
    organization_id: str = StringField("Organization ID")
    resource_id: UUID_TYPE = UUIDField("Resource ID")
    resource_name: str = StringField("Resource Name")


@resource('data-form')
class DataFormQuery(DomainQueryResource):
    """Query data forms"""

    class Meta(DomainQueryResource.Meta):
        description = "List and search data forms"
        backend_model = "data_form"

    id: UUID_TYPE = PrimaryID("Form ID")
    form_key: str = StringField("Form Key")
    title: str = StringField("Form Name")
    desc: str = StringField("Description")
    version: int = IntegerField("Version")
    owner_id: UUID_TYPE = UUIDField("Owner ID")
    organization_id: str = StringField("Organization ID")


@resource('data-element')
class DataElementQuery(DomainQueryResource):
    """Query data elements"""

    class Meta(DomainQueryResource.Meta):
        description = "List and search data elements within forms"
        scope_required = FormScope
        backend_model = "data_element"

    id: UUID_TYPE = PrimaryID("Element ID")
    form_id: UUID_TYPE = UUIDField("Form ID")
    element_type_id: UUID_TYPE = UUIDField("Element Type ID")
    element_key: str = StringField("Element Key")
    element_label: str = StringField("Element Label")
    order: int = IntegerField("Order")
    required: bool = BooleanField("Required")
    attrs: dict = DictField("Attributes", hidden=True)
    validation_rules: dict = DictField("Validation Rules", hidden=True)
    resource_id: UUID_TYPE = UUIDField("Resource ID")
    resource_name: str = StringField("Resource Name")


@resource('element-type')
class ElementTypeQuery(DomainQueryResource):
    """Query element types"""

    class Meta(DomainQueryResource.Meta):
        description = "List and search element types"
        backend_model = "element_type"

    id: UUID_TYPE = PrimaryID("Element Type ID")
    type_key: str = StringField("Type Key")
    type_name: str = StringField("Type Name")
    desc: str = StringField("Description")
    element_schema: dict = DictField("Schema Definition", hidden=True)
    attrs: dict = DictField("Attributes", hidden=True)


@resource('section')
class SectionQuery(DomainQueryResource):
    """Query sections"""

    class Meta(DomainQueryResource.Meta):
        description = "List and search sections within documents"
        scope_required = DocumentScope
        backend_model = "section"

    id: UUID_TYPE = PrimaryID("Section ID")
    document_id: UUID_TYPE = UUIDField("Document ID")
    section_key: str = StringField("Section Key")
    section_name: str = StringField("Section Name")
    desc: str = StringField("Description")
    order: int = IntegerField("Order")
    attrs: dict = DictField("Attributes", hidden=True)


@resource('document-form')
class DocumentFormQuery(DomainQueryResource):
    """Query document-form relationships"""

    class Meta(DomainQueryResource.Meta):
        description = "List document-form relationships"
        scope_required = DocumentScope
        backend_model = "document_form"

    id: UUID_TYPE = PrimaryID("Document Form ID")
    document_id: UUID_TYPE = UUIDField("Document ID")
    section_id: UUID_TYPE = UUIDField("Section ID")
    form_id: UUID_TYPE = UUIDField("Form ID")
    order: int = IntegerField("Order")
    attrs: dict = DictField("Attributes", hidden=True)


@resource('document-collection')
class DocumentCollectionQuery(DomainQueryResource):
    """Query document-collection relationships"""

    class Meta(DomainQueryResource.Meta):
        description = "List document-collection relationships"
        scope_required = CollectionScope
        backend_model = "document_collection"

    id: UUID_TYPE = PrimaryID("Document Collection ID")
    document_id: UUID_TYPE = UUIDField("Document ID")
    collection_id: UUID_TYPE = UUIDField("Collection ID")
    order: int = IntegerField("Order")
    attrs: dict = DictField("Attributes", hidden=True)

