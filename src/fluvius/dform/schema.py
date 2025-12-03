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


DEFINITION_DB_SCHEMA = config.DEFINITION_DB_SCHEMA
DFORM_DATA_DB_SCHEMA = config.DFORM_DATA_DB_SCHEMA


# --- Connector and Base Schema ---
class FormConnector(SqlaDriver):
    __db_dsn__ = config.DB_DSN
    __schema__ = DEFINITION_DB_SCHEMA


class FormDefinitionBaseSchema(FormConnector.__data_schema_base__, DomainSchema):
    __abstract__ = True


class FormDataBaseSchema(FormConnector.__data_schema_base__, DomainSchema):
    """Base schema for element data instances (stored in element schema)"""
    __abstract__ = True
    __table_args__ = {'schema': DFORM_DATA_DB_SCHEMA}


# --- Helper Functions for Foreign Keys ---
def collection_fk(constraint_name, **kwargs):
    """Create a foreign key reference to the collection table"""
    return sa.Column(pg.UUID, sa.ForeignKey(
        f'{DFORM_DATA_DB_SCHEMA}.collection._id',
        ondelete='CASCADE',
        onupdate='CASCADE',
        name=f'fk_col_{constraint_name}'
    ), nullable=False, **kwargs)


def template_fk(constraint_name, **kwargs):
    """Create a foreign key reference to the template table"""
    return sa.Column(pg.UUID, sa.ForeignKey(
        f'{DEFINITION_DB_SCHEMA}.template._id',
        ondelete='CASCADE',
        onupdate='CASCADE',
        name=f'fk_tpl_{constraint_name}'
    ), nullable=False, **kwargs)


def document_fk(constraint_name, **kwargs):
    """Create a foreign key reference to the document table"""
    return sa.Column(pg.UUID, sa.ForeignKey(
        f'{DFORM_DATA_DB_SCHEMA}.document._id',
        ondelete='CASCADE',
        onupdate='CASCADE',
        name=f'fk_doc_{constraint_name}'
    ), nullable=False, **kwargs)


def template_section_fk(constraint_name, **kwargs):
    """Create a foreign key reference to the template_section table"""
    return sa.Column(pg.UUID, sa.ForeignKey(
        f'{DEFINITION_DB_SCHEMA}.template_section._id',
        ondelete='CASCADE',
        onupdate='CASCADE',
        name=f'fk_sec_def_{constraint_name}'
    ), nullable=False, **kwargs)


def document_section_fk(constraint_name, **kwargs):
    """Create a foreign key reference to the document_section table"""
    return sa.Column(pg.UUID, sa.ForeignKey(
        f'{DFORM_DATA_DB_SCHEMA}.document_section._id',
        ondelete='CASCADE',
        onupdate='CASCADE',
        name=f'fk_doc_sec_{constraint_name}'
    ), nullable=False, **kwargs)


def form_definition_fk(constraint_name, **kwargs):
    """Create a foreign key reference to the form_definition table"""
    return sa.Column(pg.UUID, sa.ForeignKey(
        f'{DEFINITION_DB_SCHEMA}.form_definition._id',
        ondelete='CASCADE',
        onupdate='CASCADE',
        name=f'fk_form_def_{constraint_name}'
    ), nullable=False, **kwargs)


def document_form_fk(constraint_name, **kwargs):
    """Create a foreign key reference to the document_form table"""
    return sa.Column(pg.UUID, sa.ForeignKey(
        f'{DFORM_DATA_DB_SCHEMA}.document_form._id',
        ondelete='CASCADE',
        onupdate='CASCADE',
        name=f'fk_doc_form_{constraint_name}'
    ), nullable=False, **kwargs)


def form_element_group_fk(constraint_name, **kwargs):
    """Create a foreign key reference to the form_element_group table"""
    return sa.Column(pg.UUID, sa.ForeignKey(
        f'{DEFINITION_DB_SCHEMA}.form_element_group._id',
        ondelete='CASCADE',
        onupdate='CASCADE',
        name=f'fk_egrp_def_{constraint_name}'
    ), nullable=False, **kwargs)


def element_group_fk(constraint_name, **kwargs):
    """Create a foreign key reference to the element_group table"""
    return sa.Column(pg.UUID, sa.ForeignKey(
        f'{DFORM_DATA_DB_SCHEMA}.element_group._id',
        ondelete='CASCADE',
        onupdate='CASCADE',
        name=f'fk_egrp_inst_{constraint_name}'
    ), nullable=False, **kwargs)


def element_definition_fk(constraint_name, **kwargs):
    """Create a foreign key reference to the element_definition table"""
    return sa.Column(pg.UUID, sa.ForeignKey(
        f'{DEFINITION_DB_SCHEMA}.element_definition._id',
        ondelete='RESTRICT',
        onupdate='CASCADE',
        name=f'fk_elem_def_{constraint_name}'
    ), nullable=False, **kwargs)


def element_type_fk(constraint_name, **kwargs):
    """Create a foreign key reference to the element_type table"""
    return sa.Column(pg.UUID, sa.ForeignKey(
        f'{DEFINITION_DB_SCHEMA}.element_type._id',
        ondelete='RESTRICT',
        onupdate='CASCADE',
        name=f'fk_elem_type_{constraint_name}'
    ), nullable=False, **kwargs)


# ============================================================================
# TEMPLATE DEFINITIONS (Human-readable keys)
# ============================================================================


class Template(FormDefinitionBaseSchema):
    """Document templates that define the structure of documents"""
    __tablename__ = "template"
    __table_args__ = (
        sa.UniqueConstraint('template_key', name='uq_template_key'),
    )

    template_key = sa.Column(sa.String, nullable=False)
    template_name = sa.Column(sa.String, nullable=False)
    desc = sa.Column(sa.String, nullable=True)
    version = sa.Column(sa.Integer, nullable=False, default=1)
    owner_id = sa.Column(pg.UUID, nullable=True)
    organization_id = sa.Column(sa.String, nullable=True)
    collection_id = collection_fk("tpl_col_col")


class TemplateSection(FormDefinitionBaseSchema):
    """Section definitions within a template"""
    __tablename__ = "template_section"
    __table_args__ = (
        sa.UniqueConstraint('template_id', 'section_key', name='uq_tpl_sec_def_key'),
    )

    template_id = template_fk("sec_def_tpl")
    section_key = sa.Column(sa.String, nullable=False)
    section_name = sa.Column(sa.String, nullable=False)
    desc = sa.Column(sa.String, nullable=True)
    order = sa.Column(sa.Integer, nullable=False, default=0)


class TemplateForm(FormDefinitionBaseSchema):
    """Template form definitions"""
    __tablename__ = "template_form"
    __table_args__ = (
        sa.UniqueConstraint('template_id', 'form_id', name='uq_tpl_form_def_key'),
    )

    template_id = template_fk("tpl_form_def_tpl")
    form_id = form_definition_fk("tpl_form_def_form")
    section_key = sa.Column(sa.String, nullable=False)


class FormDefinition(FormDefinitionBaseSchema):
    """Form definitions within a section definition"""
    __tablename__ = "form_definition"
    __table_args__ = (
        sa.UniqueConstraint('form_key', name='uq_form_def_key'),
    )

    form_key = sa.Column(sa.String, nullable=False)
    title = sa.Column(sa.String, nullable=False)
    desc = sa.Column(sa.String, nullable=True)


class FormElementGroup(FormDefinitionBaseSchema):
    """Element group definitions within a form definition"""
    __tablename__ = "form_element_group"
    __table_args__ = (
        sa.UniqueConstraint('form_definition_id', 'group_key', name='uq_egrp_def_key'),
    )

    form_definition_id = form_definition_fk("egrp_def_form")
    group_key = sa.Column(sa.String, nullable=False)
    group_name = sa.Column(sa.String, nullable=True)
    desc = sa.Column(sa.String, nullable=True)
    order = sa.Column(sa.Integer, nullable=False, default=0)


class ElementDefinition(FormDefinitionBaseSchema):
    """Element definitions within an element group definition"""
    __tablename__ = "element_definition"
    __table_args__ = (
        sa.UniqueConstraint('element_key', name='uq_elem_def_key'),
    )

    element_key = sa.Column(sa.String, nullable=False)
    element_label = sa.Column(sa.String, nullable=True)
    element_schema = sa.Column(FluviusJSONField, nullable=False)


class FormElement(FormDefinitionBaseSchema):
    """Form element definitions within a form definition"""
    __tablename__ = "form_element"
    __table_args__ = (
        sa.UniqueConstraint('form_definition_id', 'element_key', name='uq_form_elem_def_key'),
    )

    form_definition_id = form_definition_fk("egrp_def_form")
    group_key = sa.Column(sa.String, nullable=False)
    element_key = sa.Column(sa.String, nullable=False)
    order = sa.Column(sa.Integer, nullable=False, default=0)
    required = sa.Column(sa.Boolean, nullable=False, default=False)


# ============================================================================
# DATA INSTANCES (Instance keys)
# ============================================================================

class Collection(FormDataBaseSchema):
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


class Document(FormDataBaseSchema):
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


class DocumentCollection(FormDataBaseSchema):
    """Junction table for many-to-many relationship between documents and collections"""
    __tablename__ = "document_collection"
    __table_args__ = (
        sa.UniqueConstraint('document_id', 'collection_id', name='uq_doc_col'),
    )

    document_id = document_fk("doc_col_doc")
    collection_id = collection_fk("doc_col_col")
    order = sa.Column(sa.Integer, nullable=False, default=0)


class DocumentSection(FormDataBaseSchema):
    """Section instances created from template sections"""
    __tablename__ = "document_section"
    __table_args__ = (
        sa.UniqueConstraint('document_id', 'section_key', name='uq_doc_sec_key'),
    )

    document_id = document_fk("doc_sec_doc")
    section_key = sa.Column(sa.String, nullable=False)
    section_name = sa.Column(sa.String, nullable=False)
    desc = sa.Column(sa.String, nullable=True)
    order = sa.Column(sa.Integer, nullable=False, default=0)


class DocumentForm(FormDataBaseSchema):
    """Form instances created from form definitions"""
    __tablename__ = "document_form"
    __table_args__ = (
        sa.UniqueConstraint('document_id', 'form_key', name='uq_form_inst_key'),
    )

    document_id = document_fk("form_inst_doc")
    form_key = sa.Column(sa.String, nullable=False)
    section_key = sa.Column(sa.String, nullable=False)
    title = sa.Column(sa.String, nullable=False)
    desc = sa.Column(sa.String, nullable=True)
    order = sa.Column(sa.Integer, nullable=False, default=0)
    locked = sa.Column(sa.Boolean, nullable=False, default=False)


class ElementGroupInstance(FormDataBaseSchema):
    """Element group instances created from element group definitions"""
    __tablename__ = "element_group"
    __table_args__ = (
        sa.UniqueConstraint('form_id', 'group_key', name='uq_egrp_inst_key'),
    )

    form_id = document_form_fk("egrp_inst_doc_form")
    group_key = sa.Column(sa.String, nullable=False)
    title = sa.Column(sa.String, nullable=False)
    desc = sa.Column(sa.String, nullable=True)
    order = sa.Column(sa.Integer, nullable=False, default=0)


class ElementInstance(FormDataBaseSchema):
    """Element instances created from element definitions"""
    __tablename__ = "element"
    __table_args__ = (
        sa.UniqueConstraint('form_id', 'element_key', name='uq_elem_inst_key'),
    )

    document_id = document_fk("elem_inst_doc")
    form_id = document_form_fk("elem_inst_doc_form")
    group_key = sa.Column(sa.String, nullable=False)
    element_key = sa.Column(sa.String, nullable=False)
    data = sa.Column(FluviusJSONField, nullable=True)
