"""
Form Type System

Form types are created by inheriting FormModel with element definitions
using annotation syntax.

Usage:
    class ApplicantInfoForm(FormModel):
        personal_info: FormElement("personal-info", param={"required": True})
        address: FormElement("address", param={"required": True})

        class Meta:
            key = "applicant-info"
            name = "Applicant Information"
            desc = "Primary applicant personal details"
"""
from typing import Optional, Dict, Any, ClassVar, get_origin, get_args, Annotated

from fluvius.data import DataModel
from fluvius.helper import ClassRegistry
from fluvius.error import InternalServerError

from .element import ElementModelRegistry, DataElementModel, DataElementModel
from pydantic import Field


def FormElement(
    elem_key: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    param: Optional[dict] = None,
    **kwargs
) -> Any:
    """
    Define a form element as a type annotation.

    Usage:
        class MyForm(FormModel):
            field_name: FormElement("text-field", label="Field Label")

    Args:
        elem_key: Key of the ElementModel to use
        title: Title of the element
        description: Description of the element
        required: Whether the element is required
        param: Additional element parameters

    Returns:
        Annotated type with FormElementMeta
    """
    # Create metadata
    element = ElementModelRegistry.get(elem_key)
    json_schema_extra = param or {}

    # Return Annotated type with metadata
    # Use Any as base type - the element model lookup happens at schema generation time
    return Annotated[element, Field(
        title=title or element.Meta.title,
        description=description or element.Meta.description,
        json_schema_extra=json_schema_extra,
        **kwargs
    )]


def _extract_form_elements(cls) -> Dict[str, DataElementModel]:
    """Extract FormElementMeta from class annotations"""
    elements = {}

    # Get annotations from the class (not inherited)
    annotations = getattr(cls, '__annotations__', {})

    for name, annotation in annotations.items():
        # Skip if not an Annotated type
        if get_origin(annotation) is not Annotated:
            continue
        
        # Get the args of Annotated[base_type, *metadata]
        args = get_args(annotation)
        if len(args) < 2:
            continue

        # Look for FormElementMeta in the metadata
        if issubclass(args[0], DataElementModel):
            elements[name] = args[0]
    
    return elements


class FormMeta(DataModel):
    """
    Metadata for FormModel schemas.
    
    Each FormModel subclass can define a Meta class with:
    - key: Unique identifier for the form type (required)
    - name: Human-readable name (required)
    - desc: Description (optional)
    - header: Form header text (optional)
    - footer: Form footer text (optional)
    """
    key: str
    name: str
    desc: Optional[str] = None
    header: Optional[str] = None
    footer: Optional[str] = None


class FormModel(DataModel):
    """
    Base class for form type registration.
    
    Form types are registered by creating subclasses with Meta classes
    and element definitions as type annotations:
    
    Example:
        class ApplicantInfoForm(FormModel):
            personal_info: FormElement("personal-info", param={"required": True})
            address: FormElement("address", param={"required": True})

            class Meta:
                key = "applicant-info"
                name = "Applicant Information"
                desc = "Primary applicant personal details"
    """

    class Meta:
        pass

    # Store elements extracted from annotations
    _form_elements: ClassVar[Dict[str, DataElementModel]] = {}

    def __init_subclass__(cls, **kwargs):
        """Convert Meta class to FormMeta instance and register form"""
        super().__init_subclass__(**kwargs)
        
        if cls.__dict__.get('__abstract__'):
            return
        
        if not hasattr(cls, 'Meta'):
            raise InternalServerError(
                "F00.302",
                f"FormModel subclass {cls.__name__} must define a Meta class",
                None
            )
        
        # Extract elements from annotations
        cls._form_elements = _extract_form_elements(cls)

        # Convert Meta class to FormMeta instance
        meta_cls = cls.Meta
        
        cls.Meta = FormMeta.create(meta_cls, defaults={
            'key': getattr(meta_cls, 'key', None),
            'name': getattr(meta_cls, 'name', cls.__name__),
            'desc': getattr(meta_cls, 'desc', None),
            'header': getattr(meta_cls, 'header', None),
            'footer': getattr(meta_cls, 'footer', None),
        })
        
        # Validate required fields
        if not cls.Meta.key:
            raise InternalServerError(
                "F00.303",
                f"FormModel subclass {cls.__name__} Meta must define key",
                None
            )
        
        if not cls.Meta.name:
            raise InternalServerError(
                "F00.304",
                f"FormModel subclass {cls.__name__} Meta must define name",
                None
            )
        
        # Automatically register the form in the registry using key
        FormModelRegistry.register(cls.Meta.key)(cls)
    
    @classmethod
    def get_elements(cls) -> Dict[str, DataElementModel]:
        """Get all form elements defined on this form"""
        return cls._form_elements
    
    @classmethod
    def get_element(cls, name: str) -> Optional[DataElementModel]:
        """Get a specific form element by name"""
        return cls._form_elements.get(name)
    
    @classmethod
    def to_dict(cls) -> dict:
        """Convert form model to a dictionary representation"""
        return {
            "key": cls.Meta.key,
            "name": cls.Meta.name,
            "desc": cls.Meta.desc,
            "header": cls.Meta.header,
            "footer": cls.Meta.footer,
            "elements": {
                name: elem.Meta.model_dump()
                for name, elem in cls._form_elements.items()
            }
        }


# Registry for FormModel subclasses
# Registration happens automatically via __init_subclass__
FormModelRegistry = ClassRegistry(FormModel)


__all__ = [
    "FormElement",
    "FormMeta",
    "FormModel",
    "FormModelRegistry"
]
