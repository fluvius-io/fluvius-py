"""
Form Schema Definitions

This module defines both template definitions and data instances:

Template Definitions (human-readable keys):
- Collection -> Template -> SectionDefinition -> FormDefinition -> ElementGroupDefinition -> ElementDefinition

Data Instances (instance keys):
- Collection -> Document -> SectionInstance -> FormInstance -> ElementGroupInstance -> ElementInstance
"""
from . import config

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg
from fluvius.data import DomainSchema, SqlaDriver, FluviusJSONField


DB_SCHEMA = config.DB_SCHEMA
DB_SCHEMA_ELEMENT = config.DB_SCHEMA_ELEMENT
DB_DSN = config.DB_DSN


# --- Connector and Base Schema ---
class FormConnector(SqlaDriver):
    __db_dsn__ = DB_DSN
    __schema__ = DB_SCHEMA


class FormBaseSchema(FormConnector.__data_schema_base__, DomainSchema):
    __abstract__ = True


class ElementBaseSchema(FormConnector.__data_schema_base__, DomainSchema):
    """Base schema for element data instances (stored in element schema)"""
    __abstract__ = True
    __table_args__ = {'schema': DB_SCHEMA_ELEMENT}


# --- Helper Functions for Foreign Keys ---
def collection_fk(constraint_name, **kwargs):
    """Create a foreign key reference to the collection table"""
    return sa.Column(pg.UUID, sa.ForeignKey(
        f'{DB_SCHEMA}.collection._id',
        ondelete='CASCADE',
        onupdate='CASCADE',
        name=f'fk_col_{constraint_name}'
    ), nullable=False, **kwargs)


def template_fk(constraint_name, **kwargs):
    """Create a foreign key reference to the template table"""
    return sa.Column(pg.UUID, sa.ForeignKey(
        f'{DB_SCHEMA}.template._id',
        ondelete='CASCADE',
        onupdate='CASCADE',
        name=f'fk_tpl_{constraint_name}'
    ), nullable=False, **kwargs)


def document_fk(constraint_name, **kwargs):
    """Create a foreign key reference to the document table"""
    return sa.Column(pg.UUID, sa.ForeignKey(
        f'{DB_SCHEMA}.document._id',
        ondelete='CASCADE',
        onupdate='CASCADE',
        name=f'fk_doc_{constraint_name}'
    ), nullable=False, **kwargs)


def section_definition_fk(constraint_name, **kwargs):
    """Create a foreign key reference to the section_definition table"""
    return sa.Column(pg.UUID, sa.ForeignKey(
        f'{DB_SCHEMA}.section_definition._id',
        ondelete='CASCADE',
        onupdate='CASCADE',
        name=f'fk_sec_def_{constraint_name}'
    ), nullable=False, **kwargs)


def section_instance_fk(constraint_name, **kwargs):
    """Create a foreign key reference to the section_instance table"""
    return sa.Column(pg.UUID, sa.ForeignKey(
        f'{DB_SCHEMA}.section_instance._id',
        ondelete='CASCADE',
        onupdate='CASCADE',
        name=f'fk_sec_inst_{constraint_name}'
    ), nullable=False, **kwargs)


def form_definition_fk(constraint_name, **kwargs):
    """Create a foreign key reference to the form_definition table"""
    return sa.Column(pg.UUID, sa.ForeignKey(
        f'{DB_SCHEMA}.form_definition._id',
        ondelete='CASCADE',
        onupdate='CASCADE',
        name=f'fk_form_def_{constraint_name}'
    ), nullable=False, **kwargs)


def form_instance_fk(constraint_name, **kwargs):
    """Create a foreign key reference to the form_instance table"""
    return sa.Column(pg.UUID, sa.ForeignKey(
        f'{DB_SCHEMA_ELEMENT}.form_instance._id',
        ondelete='CASCADE',
        onupdate='CASCADE',
        name=f'fk_form_inst_{constraint_name}'
    ), nullable=False, **kwargs)


def element_group_definition_fk(constraint_name, **kwargs):
    """Create a foreign key reference to the element_group_definition table"""
    return sa.Column(pg.UUID, sa.ForeignKey(
        f'{DB_SCHEMA}.element_group_definition._id',
        ondelete='CASCADE',
        onupdate='CASCADE',
        name=f'fk_egrp_def_{constraint_name}'
    ), nullable=False, **kwargs)


def element_group_instance_fk(constraint_name, **kwargs):
    """Create a foreign key reference to the element_group_instance table"""
    return sa.Column(pg.UUID, sa.ForeignKey(
        f'{DB_SCHEMA_ELEMENT}.element_group_instance._id',
        ondelete='CASCADE',
        onupdate='CASCADE',
        name=f'fk_egrp_inst_{constraint_name}'
    ), nullable=False, **kwargs)


def element_definition_fk(constraint_name, **kwargs):
    """Create a foreign key reference to the element_definition table"""
    return sa.Column(pg.UUID, sa.ForeignKey(
        f'{DB_SCHEMA}.element_definition._id',
        ondelete='RESTRICT',
        onupdate='CASCADE',
        name=f'fk_elem_def_{constraint_name}'
    ), nullable=False, **kwargs)


def element_type_fk(constraint_name, **kwargs):
    """Create a foreign key reference to the element_type table"""
    return sa.Column(pg.UUID, sa.ForeignKey(
        f'{DB_SCHEMA}.element_type._id',
        ondelete='RESTRICT',
        onupdate='CASCADE',
        name=f'fk_elem_type_{constraint_name}'
    ), nullable=False, **kwargs)


# ============================================================================
# TEMPLATE DEFINITIONS (Human-readable keys)
# ============================================================================

class Collection(FormBaseSchema):
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


class Template(FormBaseSchema):
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


class SectionDefinition(FormBaseSchema):
    """Section definitions within a template"""
    __tablename__ = "section_definition"
    __table_args__ = (
        sa.UniqueConstraint('template_id', 'section_key', name='uq_tpl_sec_def_key'),
    )

    template_id = template_fk("sec_def_tpl")
    section_key = sa.Column(sa.String, nullable=False)
    section_name = sa.Column(sa.String, nullable=False)
    desc = sa.Column(sa.String, nullable=True)
    order = sa.Column(sa.Integer, nullable=False, default=0)


class TemplateFormDefinition(FormBaseSchema):
    """Template form definitions"""
    __tablename__ = "template_form_definition"
    __table_args__ = (
        sa.UniqueConstraint('template_id', 'form_id', name='uq_tpl_form_def_key'),
    )

    template_id = template_fk("tpl_form_def_tpl")
    form_id = form_definition_fk("tpl_form_def_form")
    section_key = sa.Column(sa.String, nullable=False)


class FormDefinition(FormBaseSchema):
    """Form definitions within a section definition"""
    __tablename__ = "form_definition"
    __table_args__ = (
        sa.UniqueConstraint('form_key', name='uq_form_def_key'),
    )

    form_key = sa.Column(sa.String, nullable=False)
    title = sa.Column(sa.String, nullable=False)
    desc = sa.Column(sa.String, nullable=True)


class ElementGroupDefinition(FormBaseSchema):
    """Element group definitions within a form definition"""
    __tablename__ = "element_group_definition"
    __table_args__ = (
        sa.UniqueConstraint('form_key', 'group_key', name='uq_egrp_def_key'),
    )

    form_defintion_id = form_definition_fk("egrp_def_form")
    group_key = sa.Column(sa.String, nullable=False)
    group_name = sa.Column(sa.String, nullable=True)
    desc = sa.Column(sa.String, nullable=True)
    order = sa.Column(sa.Integer, nullable=False, default=0)


class ElementDefinition(FormBaseSchema):
    """Element definitions within an element group definition"""
    __tablename__ = "element_definition"
    __table_args__ = (
        sa.UniqueConstraint('element_key', name='uq_elem_def_key'),
    )

    element_key = sa.Column(sa.String, nullable=False)
    element_label = sa.Column(sa.String, nullable=True)
    element_schema = sa.Column(sa.FluviusJSONField, nullable=False)


class FormElementDefinition(FormBaseSchema):
    """Form element definitions within a form definition"""
    __tablename__ = "form_element_definition"
    __table_args__ = (
        sa.UniqueConstraint('form_key', 'element_key', name='uq_form_elem_def_key'),
    )

    form_defintion_id = form_definition_fk("egrp_def_form")
    group_key = element_group_definition_fk("form_elem_def_grp")
    element_key = sa.Column(sa.String, nullable=False)
    order = sa.Column(sa.Integer, nullable=False, default=0)
    required = sa.Column(sa.Boolean, nullable=False, default=False)


# ============================================================================
# DATA INSTANCES (Instance keys)
# ============================================================================

class Document(FormBaseSchema):
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


class DocumentCollection(FormBaseSchema):
    """Junction table for many-to-many relationship between documents and collections"""
    __tablename__ = "document_collection"
    __table_args__ = (
        sa.UniqueConstraint('document_id', 'collection_id', name='uq_doc_col'),
    )

    document_id = document_fk("doc_col_doc")
    collection_id = collection_fk("doc_col_col")
    order = sa.Column(sa.Integer, nullable=False, default=0)


class SectionInstance(FormBaseSchema):
    """Section instances created from section definitions"""
    __tablename__ = "section_instance"
    __table_args__ = (
        sa.UniqueConstraint('document_id', 'instance_key', name='uq_sec_inst_key'),
    )

    document_id = document_fk("sec_inst_doc")
    section_key = sa.Column(sa.String, nullable=False)
    section_name = sa.Column(sa.String, nullable=False)
    desc = sa.Column(sa.String, nullable=True)
    order = sa.Column(sa.Integer, nullable=False, default=0)


class FormInstance(ElementBaseSchema):
    """Page instances created from page definitions"""
    __tablename__ = "form_instance"
    __table_args__ = (
        sa.UniqueConstraint('section_instance_id', 'instance_key', name='uq_form_inst_key'),
    )

    section_instance_id = sa.Column(
        pg.UUID,
        sa.ForeignKey(
            f'{DB_SCHEMA}.section_instance._id',
            ondelete='CASCADE',
            onupdate='CASCADE',
            name='fk_form_inst_sec_inst'
        ),
        nullable=False
    )
    document_id = document_fk("form_inst_doc")
    form_key = sa.Column(sa.String, nullable=False)
    section_key = sa.Column(sa.String, nullable=False)
    title = sa.Column(sa.String, nullable=False)
    desc = sa.Column(sa.String, nullable=True)
    order = sa.Column(sa.Integer, nullable=False, default=0)
    locked = sa.Column(sa.Boolean, nullable=False, default=False)


class ElementGroupInstance(ElementBaseSchema):
    """Element group instances created from element group definitions"""
    __tablename__ = "element_group_instance"
    __table_args__ = (
        sa.UniqueConstraint('form_instance_id', 'group_key', name='uq_egrp_inst_key'),
    )

    form_instance_id = form_instance_fk("egrp_inst_form")
    group_key = sa.Column(sa.String, nullable=False)
    title = sa.Column(sa.String, nullable=False)
    desc = sa.Column(sa.String, nullable=True)
    order = sa.Column(sa.Integer, nullable=False, default=0)


class ElementInstance(ElementBaseSchema):
    """Element instances created from element definitions"""
    __tablename__ = "element_instance"
    __table_args__ = (
        sa.UniqueConstraint('form_instance_id', 'element_key', name='uq_elem_inst_key'),
    )

    document_id = document_fk("elem_inst_doc")
    form_instance_id = form_instance_fk("elem_inst_form")
    group_key = sa.Column(sa.String, nullable=False)
    element_key = sa.Column(sa.String, nullable=False)
    data = sa.Column(FluviusJSONField, nullable=False)
