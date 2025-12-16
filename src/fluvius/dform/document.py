"""
Document Template Structure Definitions

This module defines the structure for document templates including:
- DocumentTemplate: Top-level template definition
- DocumentSection: Section within a document
- FormRef: Reference to a FormModel by key
- TextNode, HeaderNode, GraphicNode: Content nodes
"""
from typing import Optional
from fluvius.data import DataModel
from pydantic import model_validator


class DocumentNode(DataModel):
    """Base class for all document nodes"""
    pass


class FormRef(DocumentNode):
    """Reference to a FormModel by key"""
    form_key: str
    override: dict = {}  # Override form properties (header, footer, etc.)
    
    def get_form(self):
        """Get the FormModel class referenced by this FormRef"""
        from fluvius.dform.form import FormModelRegistry
        return FormModelRegistry.get(self.form_key)


class TextNode(DocumentNode):
    """Text content node"""
    title: str
    content: str


class HeaderNode(DocumentNode):
    """Header content node"""
    header: str
    content: str = ""


class GraphicNode(DocumentNode):
    """Graphic/image content node"""
    title: str
    content: str


class DocumentSection(DocumentNode):
    """Section within a document template"""
    title: str
    children: list[DocumentNode] = []

    @model_validator(mode="after")
    def validate_section_children(self):
        """Validate section children"""
        for child in self.children:
            if not isinstance(child, DocumentNode):
                raise ValueError("All section children must be DocumentNode instances")
        return self


class DocumentTemplate(DataModel):
    """Top-level document template definition"""
    template_key: str
    title: str
    children: list[DocumentNode] = []

    @model_validator(mode="after")
    def validate_template_children(self):
        """Validate template children"""
        for child in self.children:
            if not isinstance(child, DocumentNode):
                raise ValueError("All template children must be DocumentNode instances")
        return self


__all__ = [
    "DocumentNode",
    "DocumentTemplate",
    "DocumentSection",
    "TextNode",
    "HeaderNode",
    "GraphicNode",
    "FormRef",
]
