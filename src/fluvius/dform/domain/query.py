from fluvius.query import DomainQueryManager, DomainQueryResource
from fluvius.query.field import StringField, UUIDField, IntegerField, BooleanField, DictField, PrimaryID
from fluvius.data import UUID_TYPE, DataModel

from .domain import FormDomain
from .model import FormDataManager


class CollectionScope(DataModel):
    __default_key__ = 'collection_id'
    collection_id: UUID_TYPE


class DocumentScope(DataModel):
    __default_key__ = 'document_id'
    document_id: UUID_TYPE


class FormSubmissionScope(DataModel):
    __default_key__ = 'form_submission_id'
    form_submission_id: UUID_TYPE


class FormQueryManager(DomainQueryManager):
    """Query manager for form domain"""
    __data_manager__ = FormDataManager

    class Meta(DomainQueryManager.Meta):
        prefix = FormDomain.Meta.namespace
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


@resource('template')
class TemplateQuery(DomainQueryResource):
    """Query templates"""

    class Meta(DomainQueryResource.Meta):
        description = "List and search templates"
        backend_model = "template_registry"

    id: UUID_TYPE = PrimaryID("Template ID")
    collection_id: UUID_TYPE = UUIDField("Collection ID")
    template_key: str = StringField("Template Key")
    template_name: str = StringField("Template Name")
    desc: str = StringField("Description")
    version: int = IntegerField("Version")
    owner_id: UUID_TYPE = UUIDField("Owner ID")
    organization_id: str = StringField("Organization ID")


@resource('document')
class DocumentQuery(DomainQueryResource):
    """Query documents"""

    class Meta(DomainQueryResource.Meta):
        description = "List and search documents"
        backend_model = "document"

    id: UUID_TYPE = PrimaryID("Document ID")
    template_id: UUID_TYPE = UUIDField("Template ID")
    document_key: str = StringField("Document Key")
    document_name: str = StringField("Document Name")
    desc: str = StringField("Description")
    version: int = IntegerField("Version")
    owner_id: UUID_TYPE = UUIDField("Owner ID")
    organization_id: str = StringField("Organization ID")
    resource_id: UUID_TYPE = UUIDField("Resource ID")
    resource_name: str = StringField("Resource Name")


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


@resource('document-node')
class DocumentNodeQuery(DomainQueryResource):
    """Query document nodes (sections, content, forms)"""

    class Meta(DomainQueryResource.Meta):
        description = "List and search nodes within documents"
        scope_required = DocumentScope
        backend_model = "document_node"

    id: UUID_TYPE = PrimaryID("Node ID")
    document_id: UUID_TYPE = UUIDField("Document ID")
    parent_node: UUID_TYPE = UUIDField("Parent Node ID")
    node_key: str = StringField("Node Key")
    form_key: str = StringField("Form Key")
    node_type: str = StringField("Node Type")  # section, content, form
    order: int = IntegerField("Order")
    title: str = StringField("Title")
    desc: str = StringField("Description")
    content: str = StringField("Content")
    content_type: str = StringField("Content Type")
    attrs: dict = DictField("Attributes", hidden=True)


@resource('form-registry')
class FormRegistryQuery(DomainQueryResource):
    """Query form definitions"""

    class Meta(DomainQueryResource.Meta):
        description = "List and search form definitions"
        backend_model = "form_registry"

    id: UUID_TYPE = PrimaryID("Form Registry ID")
    form_key: str = StringField("Form Key")
    title: str = StringField("Title")
    desc: str = StringField("Description")


@resource('element-registry')
class ElementRegistryQuery(DomainQueryResource):
    """Query element definitions"""

    class Meta(DomainQueryResource.Meta):
        description = "List and search element definitions"
        backend_model = "element_registry"

    id: UUID_TYPE = PrimaryID("Element Registry ID")
    element_key: str = StringField("Element Key")
    element_label: str = StringField("Element Label")
    element_schema: dict = DictField("Element Schema", hidden=True)


@resource('form-submission')
class FormSubmissionQuery(DomainQueryResource):
    """Query form instances/submissions in documents"""

    class Meta(DomainQueryResource.Meta):
        description = "List and search form submissions"
        scope_required = DocumentScope
        backend_model = "form_submission"

    id: UUID_TYPE = PrimaryID("Form Submission ID")
    document_id: UUID_TYPE = UUIDField("Document ID")
    form_reg_id: UUID_TYPE = UUIDField("Form Registry ID")
    title: str = StringField("Title")
    desc: str = StringField("Description")
    order: int = IntegerField("Order")
    locked: bool = BooleanField("Locked")
    status: str = StringField("Status")


@resource('form-element')
class FormElementQuery(DomainQueryResource):
    """Query element data instances within form submissions"""

    class Meta(DomainQueryResource.Meta):
        description = "List and search element data"
        scope_required = FormSubmissionScope
        backend_model = "form_element"

    id: UUID_TYPE = PrimaryID("Form Element ID")
    form_id: UUID_TYPE = UUIDField("Form Submission ID")
    elem_reg_id: UUID_TYPE = UUIDField("Element Registry ID")
    elem_name: str = StringField("Element Name")
    index: int = IntegerField("Index")
    required: bool = BooleanField("Required")
    data: dict = DictField("Data", hidden=True)
    status: str = StringField("Status")
