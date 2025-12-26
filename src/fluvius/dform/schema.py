"""
Form Schema Definitions

This module defines both template definitions and data instances:

Template Definitions (human-readable keys):
- Collection -> Template -> TemplateSection -> FormDefinition -> FormElementGroup -> ElementDefinition

Data Instances (instance keys):
- Collection -> Document -> DocumentSection -> DocumentForm -> ElementGroupInstance -> ElementInstance
"""
from . import config

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg
from fluvius.data import DomainSchema, SqlaDriver, FluviusJSONField


DFORM_DEFS_SCHEMA = config.DFORM_DEFS_SCHEMA
DFORM_DATA_SCHEMA = config.DFORM_DATA_SCHEMA


# --- Connector and Base Schema ---
class FormConnector(SqlaDriver):
    __db_dsn__ = config.DB_DSN
    __schema__ = DFORM_DEFS_SCHEMA


class FormRegistrySchema(FormConnector.__data_schema_base__, DomainSchema):
    __abstract__ = True
    __table_args__ = {'schema': DFORM_DEFS_SCHEMA}


class FormDataSchema(FormConnector.__data_schema_base__, DomainSchema):
    """Base schema for element data instances (stored in element schema)"""
    __abstract__ = True
    __table_args__ = {'schema': DFORM_DATA_SCHEMA}


# --- Helper Functions for Foreign Keys ---
def collection_fk(constraint_name, **kwargs):
    """Create a foreign key reference to the collection table"""
    return sa.Column(pg.UUID, sa.ForeignKey(
        f'{DFORM_DATA_SCHEMA}.collection._id',
        ondelete='CASCADE',
        onupdate='CASCADE',
        name=f'fk_col_{constraint_name}'
    ), nullable=False, **kwargs)


def template_fk(constraint_name, **kwargs):
    """Create a foreign key reference to the template table"""
    return sa.Column(pg.UUID, sa.ForeignKey(
        f'{DFORM_DEFS_SCHEMA}.template_registry._id',
        ondelete='CASCADE',
        onupdate='CASCADE',
        name=f'fk_tpl_{constraint_name}'
    ), nullable=False, **kwargs)


def document_fk(constraint_name, **kwargs):
    """Create a foreign key reference to the document table"""
    return sa.Column(pg.UUID, sa.ForeignKey(
        f'{DFORM_DATA_SCHEMA}.document._id',
        ondelete='CASCADE',
        onupdate='CASCADE',
        name=f'fk_doc_{constraint_name}'
    ), nullable=False, **kwargs)


def template_section_fk(constraint_name, **kwargs):
    """Create a foreign key reference to the template_section table"""
    return sa.Column(pg.UUID, sa.ForeignKey(
        f'{DFORM_DEFS_SCHEMA}.template_section._id',
        ondelete='CASCADE',
        onupdate='CASCADE',
        name=f'fk_sec_def_{constraint_name}'
    ), nullable=False, **kwargs)


def document_section_fk(constraint_name, **kwargs):
    """Create a foreign key reference to the document_section table"""
    return sa.Column(pg.UUID, sa.ForeignKey(
        f'{DFORM_DATA_SCHEMA}.document_section._id',
        ondelete='CASCADE',
        onupdate='CASCADE',
        name=f'fk_doc_sec_{constraint_name}'
    ), nullable=False, **kwargs)


def form_registry_fk(constraint_name, **kwargs):
    """Create a foreign key reference to the form_registry table"""
    return sa.Column(pg.UUID, sa.ForeignKey(
        f'{DFORM_DEFS_SCHEMA}.form_registry._id',
        ondelete='CASCADE',
        onupdate='CASCADE',
        name=f'fk_form_reg_{constraint_name}'
    ), nullable=False, **kwargs)


def form_submission_fk(constraint_name, **kwargs):
    """Create a foreign key reference to the form_submission table"""
    return sa.Column(pg.UUID, sa.ForeignKey(
        f'{DFORM_DATA_SCHEMA}.form_submission._id',
        ondelete='CASCADE',
        onupdate='CASCADE',
        name=f'fk_form_sub_{constraint_name}'
    ), nullable=False, **kwargs)


def form_element_fk(constraint_name, **kwargs):
    """Create a foreign key reference to the form_element table"""
    return sa.Column(pg.UUID, sa.ForeignKey(
        f'{DFORM_DEFS_SCHEMA}.form_element._id',
        ondelete='CASCADE',
        onupdate='CASCADE',
        name=f'fk_form_elem_{constraint_name}'
    ), nullable=False, **kwargs)


def element_registry_fk(constraint_name, **kwargs):
    """Create a foreign key reference to the element_registry table"""
    return sa.Column(pg.UUID, sa.ForeignKey(
        f'{DFORM_DEFS_SCHEMA}.element_registry._id',
        ondelete='CASCADE',
        onupdate='CASCADE',
        name=f'fk_elem_reg_{constraint_name}'
    ), nullable=False, **kwargs)



# ============================================================================
# TEMPLATE DEFINITIONS (Human-readable keys)
# ============================================================================


class TemplateRegistry(FormRegistrySchema):
    """Document templates that define the structure of documents"""
    __tablename__ = "template_registry"
    __table_args__ = (
        sa.UniqueConstraint('template_key', name='uq_template_key'),
    )

    serial_no = sa.Column(sa.BigInteger, sa.Sequence('template_registry_serial_seq', schema=DFORM_DEFS_SCHEMA), nullable=False, unique=True)
    template_key = sa.Column(sa.String, nullable=False)
    template_name = sa.Column(sa.String, nullable=False)
    desc = sa.Column(sa.String, nullable=True)
    version = sa.Column(sa.Integer, nullable=False, default=1)
    owner_id = sa.Column(pg.UUID, nullable=True)
    organization_id = sa.Column(sa.String, nullable=True)
    collection_id = collection_fk("tpl_col_col")

class FormRegistry(FormRegistrySchema):
    """Form definitions within a section definition"""
    __tablename__ = "form_registry"
    __table_args__ = (
        sa.UniqueConstraint('form_key', name='uq_form_def_key'),
    )

    serial_no = sa.Column(sa.BigInteger, sa.Sequence('form_registry_serial_seq', schema=DFORM_DEFS_SCHEMA), nullable=False, unique=True)
    form_key = sa.Column(sa.String, nullable=False)
    title = sa.Column(sa.String, nullable=False)
    desc = sa.Column(sa.String, nullable=True)


class ElementRegistry(FormRegistrySchema):
    """Element definitions within an element group definition"""
    __tablename__ = "element_registry"
    __table_args__ = (
        sa.UniqueConstraint('element_key', name='uq_elem_def_key'),
    )

    serial_no = sa.Column(sa.BigInteger, sa.Sequence('element_registry_serial_seq', schema=DFORM_DEFS_SCHEMA), nullable=False, unique=True)
    element_key = sa.Column(sa.String, nullable=False)
    element_label = sa.Column(sa.String, nullable=True)
    element_schema = sa.Column(FluviusJSONField, nullable=False)

# ============================================================================
# DATA INSTANCES (Instance keys)
# ============================================================================

class Collection(FormDataSchema):
    """Collections that can contain multiple templates and documents"""
    __tablename__ = "collection"
    __table_args__ = (
        sa.UniqueConstraint('collection_key', name='uq_collection_key'),
    )

    collection_key = sa.Column(sa.String, nullable=False)
    collection_name = sa.Column(sa.String, nullable=False)
    desc = sa.Column(sa.String, nullable=True)
    owner_id = sa.Column(pg.UUID, nullable=True)
    organization_id = sa.Column(sa.String, nullable=True)


class Document(FormDataSchema):
    """Document instances created from templates"""
    __tablename__ = "document"
    __table_args__ = (
        sa.UniqueConstraint('document_key', name='uq_doc_key'),
    )

    template_id = template_fk("doc_tpl")
    document_key = sa.Column(sa.String, nullable=False)
    document_name = sa.Column(sa.String, nullable=False)
    desc = sa.Column(sa.String, nullable=True)
    version = sa.Column(sa.Integer, nullable=False, default=1)
    owner_id = sa.Column(pg.UUID, nullable=True)
    organization_id = sa.Column(sa.String, nullable=True)
    resource_id = sa.Column(pg.UUID, nullable=True)  # Optional reference to linked resource
    resource_name = sa.Column(sa.String, nullable=True)  # Optional resource name


class DocumentCollection(FormDataSchema):
    """Junction table for many-to-many relationship between documents and collections"""
    __tablename__ = "document_collection"
    __table_args__ = (
        sa.UniqueConstraint('document_id', 'collection_id', name='uq_doc_col'),
    )

    document_id = document_fk("doc_col_doc")
    collection_id = collection_fk("doc_col_col")
    order = sa.Column(sa.Integer, nullable=False, default=0)


class DocumentNode(FormDataSchema):
    """
    Document nodes for storing all types of content within a document.
    
    Supports multiple node types:
    - "section": Container node with children (title, desc)
    - "content": Text/header/graphic content (title, content, ctype)
    - "form": Form reference (form_key, attrs for overrides)
    """
    __tablename__ = "document_node"
    __table_args__ = (
        sa.UniqueConstraint('document_id', 'node_key', name='uq_doc_node_key'),
    )

    document_id = document_fk("doc_node_doc")
    parent_node = sa.Column(pg.UUID, nullable=True)  # Self-referential for nesting
    node_key = sa.Column(sa.String, nullable=False)  # Unique key within document
    form_key = sa.Column(sa.String, nullable=True)  # Reference to form registry (for form nodes)
    node_type = sa.Column(sa.String, nullable=False, default="section")  # "section", "content", "form"
    order = sa.Column(sa.Integer, nullable=False, default=0)
    
    # Common fields
    title = sa.Column(sa.String, nullable=True)  # Title for sections and content
    desc = sa.Column(sa.String, nullable=True)  # Description
    
    # Content node fields
    content = sa.Column(sa.Text, nullable=True)  # Content text/html/markdown
    content_type = sa.Column(sa.String, nullable=True)  # Content type: "text", "header", "graphic", "html", "markdown"
    
   
    # Extensible attributes (overrides, metadata, styling, etc.)
    attrs = sa.Column(FluviusJSONField, nullable=True)


class FormSubmission(FormDataSchema):
    """Form instances created from form definitions"""
    __tablename__ = "form_submission"
    __table_args__ = (
        sa.UniqueConstraint('document_id', 'form_key', name='uq_form_inst_key'),
    )

    document_id = document_fk("form_inst_doc")
    form_key = sa.Column(sa.String, nullable=False)
    title = sa.Column(sa.String, nullable=False)
    desc = sa.Column(sa.String, nullable=True)
    order = sa.Column(sa.Integer, nullable=False, default=0)
    locked = sa.Column(sa.Boolean, nullable=False, default=False)
    status = sa.Column(sa.String, nullable=False, default="draft")


class FormElement(FormDataSchema):
    """Element instances created from element definitions"""
    __tablename__ = "form_element"
    __table_args__ = (
        sa.UniqueConstraint('form_submission_id', 'element_registry_id', 'index', name='uq_form_element_name'),
    )

    form_submission_id = form_submission_fk("form_elem_form_sub")
    element_registry_id = element_registry_fk("form_elem_elem_reg")
    element_name = sa.Column(sa.String, nullable=False)
    index = sa.Column(sa.Integer, nullable=False, default=-1)
    required = sa.Column(sa.Boolean, nullable=False, default=False)
    data = sa.Column(FluviusJSONField, nullable=True)
    status = sa.Column(sa.String, nullable=False, default="draft")
