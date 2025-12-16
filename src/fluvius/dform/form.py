"""
Form Type System

Form types are created by inheriting FormModel with element definitions.
Each form model defines a reusable form structure with elements.

Usage:
    class ApplicantInfoFormModel(FormModel):
        class Meta:
            key = "applicant-info"
            name = "Applicant Information"
            desc = "Primary applicant personal details"
            elements = {
                "personal_info": FormElement(elem_key="personal-info", param={"required": True}),
                "address": FormElement(elem_key="address", param={"required": True}),
            }
"""
from typing import Optional, Dict, Any, ClassVar, Type, Annotated
from pydantic import Field as PydanticField


from fluvius.data import DataModel
from fluvius.helper import ClassRegistry, camel_to_lower
from fluvius.error import InternalServerError
from .element import ElementModelRegistry


def FormElement(
    elem_key,
    label=None,
    required=False,
    **kwargs
):
    elem_def = ElementModelRegistry.get(elem_key)
    if not elem_def:
        raise InternalServerError(
            "F00.305",
            f"Element definition not found for key: {elem_key}",
            None
        )
        
    
    return Annotated[elem_def, PydanticField(label=label, required=required, **kwargs)]


class FormMeta(DataModel):
    """
    Metadata for FormModel schemas.
    
    Each FormModel subclass can define a Meta class with:
    - key: Unique identifier for the form type (required)
    - name: Human-readable name (required)
    - desc: Description (optional)
    - header: Form header text (optional)
    - footer: Form footer text (optional)
    - elements: Dictionary of form elements (optional)
    """
    key: str
    name: str
    desc: Optional[str] = None
    header: Optional[str] = None
    footer: Optional[str] = None
    elements: Dict[str, FormElement] = {}


class FormModel(DataModel):
    """
    Base class for form type registration.
    
    This class is used for registering form types via Meta classes.
    Elements are defined in the Meta class as a dictionary.
    
    Form types are registered by creating subclasses with Meta classes:
    
    Example:
        class ApplicantInfoFormModel(FormModel):
            class Meta:
                key = "applicant-info"
                name = "Applicant Information"
                desc = "Primary applicant personal details"
                elements = {
                    "personal_info": FormElement(elem_key="personal-info", param={"required": True}),
                    "address": FormElement(elem_key="address", param={"required": True}),
                }
    """

    class Meta:
        pass

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
        
        # Convert Meta class to FormMeta instance
        meta_cls = cls.Meta
        
        # Get elements from Meta class
        elements = getattr(meta_cls, 'elements', {})
        
        cls.Meta = FormMeta.create(meta_cls, defaults={
            'key': getattr(meta_cls, 'key', None),
            'name': getattr(meta_cls, 'name', cls.__name__),
            'desc': getattr(meta_cls, 'desc', None),
            'header': getattr(meta_cls, 'header', None),
            'footer': getattr(meta_cls, 'footer', None),
            'elements': elements,
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
    def get_elements(cls) -> Dict[str, FormElement]:
        """Get all form elements defined on this form"""
        return cls.Meta.elements
    
    @classmethod
    def get_element(cls, name: str) -> Optional[FormElement]:
        """Get a specific form element by name"""
        return cls.Meta.elements.get(name)
    
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
                name: {
                    "elem_key": elem.elem_key,
                    "param": elem.param,
                    "label": elem.label,
                    "required": elem.required,
                }
                for name, elem in cls.Meta.elements.items()
            }
        }


# Registry for FormModel subclasses
# Registration happens automatically via __init_subclass__
FormModelRegistry = ClassRegistry(FormModel)


__all__ = [
    "FormElement",
    "FormMeta",
    "FormModel",
    "FormModelRegistry",
]
