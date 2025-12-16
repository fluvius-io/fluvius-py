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

from .element import ElementModelRegistry, ElementModel
from pydantic import Field


class FormElementMeta:
    """Metadata for form element annotations"""
    def __init__(self, elem_key: str, label: Optional[str] = None, required: bool = False, param: dict = None):
        self.elem_key = elem_key
        self.label = label
        self.required = required
        self.param = param or {}

    def to_dict(self) -> dict:
        return {
            "elem_key": self.elem_key,
            "label": self.label,
            "required": self.required,
            "param": self.param,
        }


def FormElement(
    elem_key: str,
    label: Optional[str] = None,
    required: bool = False,
    param: dict = None,
    **kwargs
) -> Any:
    """
    Define a form element as a type annotation.

    Usage:
        class MyForm(FormModel):
            field_name: FormElement("text-field", label="Field Label")

    Args:
        elem_key: Key of the ElementModel to use
        label: Display label for the element
        required: Whether the element is required
        param: Additional element parameters

    Returns:
        Annotated type with FormElementMeta
    """
    # Create metadata
    element = ElementModelRegistry.get(elem_key)
    # meta = FormElementMeta(
    #     elem_key=elem_key,
    #     label=label,
    #     required=required,
    #     param=param or {}
    # )

    # Return Annotated type with metadata
    # Use Any as base type - the element model lookup happens at schema generation time
    return Annotated[element, Field(title=element.Meta.name, **kwargs)]


def _extract_form_elements(cls) -> Dict[str, FormElementMeta]:
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
        if issubclass(args[0], ElementModel):
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
    _form_elements: ClassVar[Dict[str, ElementModel]] = {}

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
    def get_elements(cls) -> Dict[str, ElementModel]:
        """Get all form elements defined on this form"""
        return cls._form_elements
    
    @classmethod
    def get_element(cls, name: str) -> Optional[ElementModel]:
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

    # @classmethod
    # def model_json_schema(cls) -> dict:
    #     """Generate JSON schema for the form including all elements"""
    #     from .element import ElementModelRegistry

    #     properties = {}
    #     required = []

    #     for name, elem_meta in cls._form_elements.items():
    #         elem_cls = ElementModelRegistry.get(elem_meta.elem_key)
    #         if elem_cls is not None:
    #             # Get the element's JSON schema
    #             elem_schema = elem_cls.model_json_schema()
    #             properties[name] = {
    #                 **elem_schema,
    #                 "title": elem_meta.label or name,
    #                 "x-elem-key": elem_meta.elem_key,
    #                 "x-param": elem_meta.param,
    #             }
    #         else:
    #             # Element not registered - use a placeholder
    #             properties[name] = {
    #                 "type": "object",
    #                 "title": elem_meta.label or name,
    #                 "x-elem-key": elem_meta.elem_key,
    #                 "x-param": elem_meta.param,
    #             }

    #         if elem_meta.required:
    #             required.append(name)

    #     return {
    #         "type": "object",
    #         "title": cls.Meta.name,
    #         "description": cls.Meta.desc,
    #         "properties": properties,
    #         "required": required if required else None,
    #         "x-form-key": cls.Meta.key,
    #         "x-header": cls.Meta.header,
    #         "x-footer": cls.Meta.footer,
    #     }


# Registry for FormModel subclasses
# Registration happens automatically via __init_subclass__
FormModelRegistry = ClassRegistry(FormModel)


__all__ = [
    "FormElement",
    "FormMeta",
    "FormModel",
    "FormModelRegistry",
    "ElementModel"
]
