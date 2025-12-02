from . import config

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg
from fluvius.data import DomainSchema, SqlaDriver, FluviusJSONField


DB_SCHEMA = config.DB_SCHEMA
DB_DSN = config.DB_DSN


# --- Connector and Base Schema ---
class FormConnector(SqlaDriver):
    __db_dsn__ = DB_DSN
    __schema__ = DB_SCHEMA


class FormBaseSchema(FormConnector.__data_schema_base__, DomainSchema):
    __abstract__ = True


# --- Helper Functions for Foreign Keys ---
def element_type_fk(constraint_name, **kwargs):
    """Create a foreign key reference to the element_type table"""
    return sa.Column(pg.UUID, sa.ForeignKey(
        f'{DB_SCHEMA}.element_type._id',
        ondelete='RESTRICT',
        onupdate='CASCADE',
        name=f'fk_element_type_{constraint_name}'
    ), nullable=False, **kwargs)


def data_form_fk(constraint_name, **kwargs):
    """Create a foreign key reference to the data_form table"""
    return sa.Column(pg.UUID, sa.ForeignKey(
        f'{DB_SCHEMA}.data_form._id',
        ondelete='CASCADE',
        onupdate='CASCADE',
        name=f'fk_data_form_{constraint_name}'
    ), nullable=False, **kwargs)


def document_fk(constraint_name, **kwargs):
    """Create a foreign key reference to the document table"""
    return sa.Column(pg.UUID, sa.ForeignKey(
        f'{DB_SCHEMA}.document._id',
        ondelete='CASCADE',
        onupdate='CASCADE',
        name=f'fk_document_{constraint_name}'
    ), nullable=False, **kwargs)


def section_fk(constraint_name, **kwargs):
    """Create a foreign key reference to the section table"""
    return sa.Column(pg.UUID, sa.ForeignKey(
        f'{DB_SCHEMA}.section._id',
        ondelete='CASCADE',
        onupdate='CASCADE',
        name=f'fk_section_{constraint_name}'
    ), nullable=False, **kwargs)


def collection_fk(constraint_name, **kwargs):
    """Create a foreign key reference to the collection table"""
    return sa.Column(pg.UUID, sa.ForeignKey(
        f'{DB_SCHEMA}.collection._id',
        ondelete='CASCADE',
        onupdate='CASCADE',
        name=f'fk_collection_{constraint_name}'
    ), nullable=False, **kwargs)


# --- Models ---
class ElementType(FormBaseSchema):
    """Base element types that define the structure and behavior of form elements"""
    __tablename__ = "element_type"
    __table_args__ = (
        sa.UniqueConstraint('type_key', name='uq_element_type_key'),
    )

    type_key = sa.Column(sa.String, nullable=False)
    type_name = sa.Column(sa.String, nullable=False)
    desc = sa.Column(sa.String, nullable=True)
    element_schema = sa.Column(FluviusJSONField, nullable=True)  # DataModel class name for element validation
    attrs = sa.Column(FluviusJSONField, nullable=True)  # Additional configuration


class DataForm(FormBaseSchema):
    """Forms that contain multiple data elements"""
    __tablename__ = "data_form"
    __table_args__ = (
        sa.UniqueConstraint('form_key', name='uq_data_form_key'),
    )

    form_key = sa.Column(sa.String, nullable=False)
    form_name = sa.Column(sa.String, nullable=False)
    desc = sa.Column(sa.String, nullable=True)
    version = sa.Column(sa.Integer, nullable=False, default=1)
    attrs = sa.Column(FluviusJSONField, nullable=True)  # Form-level configuration
    owner_id = sa.Column(pg.UUID, nullable=True)
    organization_id = sa.Column(sa.String, nullable=True)


class DataElement(FormBaseSchema):
    """Elements within a form, derived from an ElementType"""
    __tablename__ = "data_element"
    __table_args__ = (
        sa.UniqueConstraint('form_id', 'element_key', name='uq_data_element_form_key'),
    )

    form_id = data_form_fk("element_form_id")
    element_type_id = element_type_fk("element_type_id")
    element_key = sa.Column(sa.String, nullable=False)
    element_label = sa.Column(sa.String, nullable=True)
    order = sa.Column(sa.Integer, nullable=False, default=0)
    required = sa.Column(sa.Boolean, nullable=False, default=False)
    attrs = sa.Column(FluviusJSONField, nullable=True)  # Element-specific configuration
    validation_rules = sa.Column(FluviusJSONField, nullable=True)  # Validation rules
    resource_id = sa.Column(pg.UUID, nullable=True)  # Optional reference to linked resource
    resource_name = sa.Column(sa.String, nullable=True)  # Optional resource name


class Document(FormBaseSchema):
    """Documents that combine multiple forms organized by sections"""
    __tablename__ = "document"
    __table_args__ = (
        sa.UniqueConstraint('document_key', name='uq_document_key'),
    )

    document_key = sa.Column(sa.String, nullable=False)
    document_name = sa.Column(sa.String, nullable=False)
    desc = sa.Column(sa.String, nullable=True)
    version = sa.Column(sa.Integer, nullable=False, default=1)
    attrs = sa.Column(FluviusJSONField, nullable=True)  # Document-level configuration
    owner_id = sa.Column(pg.UUID, nullable=True)
    organization_id = sa.Column(sa.String, nullable=True)
    resource_id = sa.Column(pg.UUID, nullable=True)  # Optional reference to linked resource
    resource_name = sa.Column(sa.String, nullable=True)  # Optional resource name


class Section(FormBaseSchema):
    """Sections that organize forms within a document"""
    __tablename__ = "section"
    __table_args__ = (
        sa.UniqueConstraint('document_id', 'section_key', name='uq_section_document_key'),
    )

    document_id = document_fk("section_document_id")
    section_key = sa.Column(sa.String, nullable=False)
    section_name = sa.Column(sa.String, nullable=False)
    desc = sa.Column(sa.String, nullable=True)
    order = sa.Column(sa.Integer, nullable=False, default=0)
    attrs = sa.Column(FluviusJSONField, nullable=True)  # Section-level configuration


class DocumentForm(FormBaseSchema):
    """Junction table linking documents to forms through sections"""
    __tablename__ = "document_form"
    __table_args__ = (
        sa.UniqueConstraint('document_id', 'section_id', 'form_id', name='uq_document_form'),
    )

    document_id = document_fk("document_form_document_id")
    section_id = sa.Column(pg.UUID, sa.ForeignKey(
        f'{DB_SCHEMA}.section._id',
        ondelete='CASCADE',
        onupdate='CASCADE',
        name='fk_section_document_form_section_id'
    ), nullable=True)  # Optional: forms can be added directly to documents
    form_id = data_form_fk("document_form_form_id")
    order = sa.Column(sa.Integer, nullable=False, default=0)
    attrs = sa.Column(FluviusJSONField, nullable=True)  # Relationship-specific configuration


class Collection(FormBaseSchema):
    """Collections that can contain multiple documents"""
    __tablename__ = "collection"
    __table_args__ = (
        sa.UniqueConstraint('collection_key', name='uq_collection_key'),
    )

    collection_key = sa.Column(sa.String, nullable=False)
    collection_name = sa.Column(sa.String, nullable=False)
    desc = sa.Column(sa.String, nullable=True)
    attrs = sa.Column(FluviusJSONField, nullable=True)  # Collection-level configuration
    owner_id = sa.Column(pg.UUID, nullable=True)
    organization_id = sa.Column(sa.String, nullable=True)


class DocumentCollection(FormBaseSchema):
    """Junction table for many-to-many relationship between documents and collections"""
    __tablename__ = "document_collection"
    __table_args__ = (
        sa.UniqueConstraint('document_id', 'collection_id', name='uq_document_collection'),
    )

    document_id = document_fk("doc_col_document_id")
    collection_id = collection_fk("doc_col_collection_id")
    order = sa.Column(sa.Integer, nullable=False, default=0)
    attrs = sa.Column(FluviusJSONField, nullable=True)  # Relationship-specific configuration

