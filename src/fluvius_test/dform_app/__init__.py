"""
DForm Test App - Sample Element Models

This module contains sample ElementModel definitions for testing
the DForm element schema system.

Usage:
    # Import to register element models
    import fluvius_test.dform_app
    
    # Or import specific elements
    from fluvius_test.dform_app import PersonalInfoElement, AddressElement
"""

from .elements import (
    # Personal Information
    PersonalInfoElement,
    
    # Contact Information
    AddressElement,
    PhoneNumberElement,
    EmailElement,
    
    # Form Inputs
    TextFieldElement,
    TextAreaElement,
    NumberFieldElement,
    DateFieldElement,
    SelectFieldElement,
    CheckboxElement,
    RadioGroupElement,
    
    # File Uploads
    FileUploadElement,
    ImageUploadElement,
    
    # Special
    SignatureElement,
    RatingElement,
)

__all__ = [
    "PersonalInfoElement",
    "AddressElement",
    "PhoneNumberElement",
    "EmailElement",
    "TextFieldElement",
    "TextAreaElement",
    "NumberFieldElement",
    "DateFieldElement",
    "SelectFieldElement",
    "CheckboxElement",
    "RadioGroupElement",
    "FileUploadElement",
    "ImageUploadElement",
    "SignatureElement",
    "RatingElement",
]
