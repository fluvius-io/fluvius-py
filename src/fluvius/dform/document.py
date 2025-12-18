"""
Document Template Structure Definitions

This module defines the structure for document templates including:
- DocumentTemplate: Top-level template definition
- DocumentSection: Section within a document
- FormRef: Reference to a FormModel by key
- ContentNode: Text/header/graphic content nodes
- DocumentTemplateRegistry: Registry for document templates
"""
from typing import Optional, Union
from fluvius.data import DataModel
from fluvius.error import BadRequestError, NotFoundError
from pydantic import model_validator
from fluvius.dform.form import FormModelRegistry

from . import logger


class DocumentNode(DataModel):
    """Base class for all document nodes"""
    title: str
    content: str
    content_type: str = "text"  # "text", "header", "graphic", etc.
 
    def to_json(self) -> dict:
        """Convert node to JSON-serializable dict"""
        return {
            "node_type": self.__class__.__name__,
            **self.model_dump()
        }


class ContentNode(DocumentNode):
    """Content node for text, headers, or graphics"""

    def to_json(self) -> dict:
        """Convert content node to JSON"""
        return {
            "node_type": "ContentNode",
            "title": self.title,
            "content": self.content,
            "ctype": self.ctype
        }


class FormNode(DocumentNode):
    """Reference to a FormModel by key"""
    form_key: str
    attrs: dict = {}  # Override form properties (header, footer, etc.)
    
    @model_validator(mode='after')
    def validate_form_key(self):
        if FormModelRegistry.get(self.form_key) is None:
            raise ValueError(f"Form model not found: {self.form_key}")

        return self


class DocumentSection(DocumentNode):
    """Section within a document template"""
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


class _DocumentTemplateRegistry:
    """
    Registry for DocumentTemplate instances.
    
    This registry stores document templates by their template_key and provides
    methods to register, retrieve, and list templates.
    
    Usage:
        # Register a template
        DocumentTemplateRegistry.register(my_template)
        
        # Or use decorator style
        @DocumentTemplateRegistry.register
        def create_template():
            return DocumentTemplate(template_key="my-template", title="My Template")
        
        # Get a template by key
        template = DocumentTemplateRegistry.get("my-template")
        
        # List all registered templates
        all_templates = DocumentTemplateRegistry.keys()
    """
    
    def __init__(self):
        self._registry: dict[str, DocumentTemplate] = {}
    
    def register(self, template_or_func=None, /, *, key: Optional[str] = None):
        """
        Register a DocumentTemplate instance.
        
        Can be used in multiple ways:
        1. Direct registration: DocumentTemplateRegistry.register(template)
        2. With custom key: DocumentTemplateRegistry.register(template, key="custom-key")
        3. As decorator: @DocumentTemplateRegistry.register
        
        Args:
            template_or_func: DocumentTemplate instance or callable that returns one
            key: Optional custom key (defaults to template.template_key)
            
        Returns:
            The registered template or a decorator function
        """
        def _register(template: DocumentTemplate) -> DocumentTemplate:
            if not isinstance(template, DocumentTemplate):
                raise BadRequestError(
                    "F00.401",
                    f"Only DocumentTemplate instances can be registered, got: {type(template).__name__}"
                )
            
            template_key = key or template.template_key
            
            if template_key in self._registry:
                raise BadRequestError(
                    "F00.402",
                    f"Template with key '{template_key}' is already registered"
                )
            
            self._registry[template_key] = template
            logger.debug(f"Registered DocumentTemplate: {template_key}")
            return template
        
        # Handle callable (factory function or decorated function)
        if callable(template_or_func) and not isinstance(template_or_func, DocumentTemplate):
            result = template_or_func()
            return _register(result)
        
        # Direct registration
        if template_or_func is not None:
            return _register(template_or_func)
        
        # Return decorator for deferred registration
        return _register
    
    def get(self, template_key: str) -> DocumentTemplate:
        """
        Get a registered template by key.
        
        Args:
            template_key: The template key to look up
            
        Returns:
            The registered DocumentTemplate
            
        Raises:
            NotFoundError: If template is not registered
        """
        try:
            return self._registry[template_key]
        except KeyError:
            raise NotFoundError(
                "F00.403",
                f"DocumentTemplate '{template_key}' not found in registry. Available: {list(self._registry.keys())}"
            )
    
    def exists(self, template_key: str) -> bool:
        """Check if a template is registered."""
        return template_key in self._registry
    
    def keys(self) -> tuple[str, ...]:
        """Get all registered template keys."""
        return tuple(self._registry.keys())
    
    def values(self) -> tuple[DocumentTemplate, ...]:
        """Get all registered templates."""
        return tuple(self._registry.values())
    
    def items(self) -> tuple[tuple[str, DocumentTemplate], ...]:
        """Get all registered (key, template) pairs."""
        return tuple(self._registry.items())
    
    def unregister(self, template_key: str) -> Optional[DocumentTemplate]:
        """
        Remove a template from the registry.
        
        Args:
            template_key: The template key to remove
            
        Returns:
            The removed template, or None if not found
        """
        return self._registry.pop(template_key, None)
    
    def clear(self):
        """Clear all registered templates."""
        self._registry.clear()
    
    def __len__(self) -> int:
        return len(self._registry)
    
    def __contains__(self, template_key: str) -> bool:
        return template_key in self._registry
    
    def __iter__(self):
        return iter(self._registry)


# Global registry instance
DocumentTemplateRegistry = _DocumentTemplateRegistry()


__all__ = [
    "DocumentNode",
    "DocumentTemplate",
    "DocumentTemplateRegistry",
    "DocumentSection",
    "ContentNode",
    "FormNode",
]
