"""
Document Template Structure Definitions

This module defines the structure for document templates including:
- DocumentTemplate: Top-level template definition
- DocumentSection: Section within a document
- FormRef: Reference to a FormModel by key
- TextNode, HeaderNode, GraphicNode: Content nodes
"""
from typing import Union
from fluvius.data import DataModel
from pydantic import model_validator


class DocumentNode(DataModel):
    """Base class for all document nodes"""
    
    def to_json(self) -> dict:
        """Convert node to JSON-serializable dict"""
        return {
            "node_type": self.__class__.__name__,
            **self.model_dump()
        }


class FormNode(DocumentNode):
    """Reference to a FormModel by key"""
    form_key: str
    override: dict = {}  # Override form properties (header, footer, etc.)
    
    def get_form(self):
        """Get the FormModel class referenced by this FormRef"""
        from fluvius.dform.form import FormModelRegistry
        return FormModelRegistry.get(self.form_key)


class ContentNode(DocumentNode):
    """Graphic/image content node"""
    title: str
    content: str
    ctype: str


class DocumentSection(DocumentNode):
    """Section within a document template"""
    title: str
    children: list["AnyDocumentNode"] = []

    @model_validator(mode="after")
    def validate_section_children(self):
        """Validate section children"""
        for child in self.children:
            if not isinstance(child, DocumentNode):
                raise ValueError("All section children must be DocumentNode instances")
        return self
    
    def to_json(self) -> dict:
        """Convert section to JSON with properly serialized children"""
        return {
            "node_type": "DocumentSection",
            "title": self.title,
            "children": [child.to_json() for child in self.children]
        }


# Type alias for any document node type
AnyDocumentNode = Union[FormNode, ContentNode, DocumentSection]


class DocumentTemplate(DataModel):
    """Top-level document template definition"""
    template_key: str
    title: str
    children: list[AnyDocumentNode] = []

    @model_validator(mode="after")
    def validate_template_children(self):
        """Validate template children"""
        for child in self.children:
            if not isinstance(child, DocumentNode):
                raise ValueError("All template children must be DocumentNode instances")
        return self

    def to_json(self) -> dict:
        """
        Generate JSON presentation of the DocumentTemplate.
        
        Returns:
            JSON-serializable dictionary of the template data
        """
        return {
            "node_type": "DocumentTemplate",
            "template_key": self.template_key,
            "title": self.title,
            "children": [child.to_json() for child in self.children]
        }


__all__ = [
    "DocumentNode",
    "DocumentTemplate",
    "DocumentSection",
    "ContentNode",
    "FormNode",
]
