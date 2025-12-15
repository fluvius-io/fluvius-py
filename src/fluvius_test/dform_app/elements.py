"""
Sample Element Models for DForm Testing

This module provides a comprehensive set of ElementModel definitions
that can be used for testing the DForm element schema system.
"""
from typing import Optional, List
from datetime import date
from pydantic import Field, EmailStr
from enum import Enum

from fluvius.dform.element import ElementModel


# ============================================================================
# Personal Information Elements
# ============================================================================

class PersonalInfoElement(ElementModel):
    """Personal information element for collecting name, DOB, etc."""
    first_name: str = Field(description="First name")
    last_name: str = Field(description="Last name")
    middle_name: Optional[str] = Field(default=None, description="Middle name")
    date_of_birth: Optional[date] = Field(default=None, description="Date of birth")
    gender: Optional[str] = Field(default=None, description="Gender")
    
    class Meta:
        key = "personal-info"
        name = "Personal Information"
        desc = "Collects personal information including name and date of birth"
        table_name = "elem_personal_info"


class AddressElement(ElementModel):
    """Address element for collecting physical addresses."""
    street_line1: str = Field(description="Street address line 1")
    street_line2: Optional[str] = Field(default=None, description="Street address line 2")
    city: str = Field(description="City")
    state: str = Field(description="State/Province")
    postal_code: str = Field(description="Postal/ZIP code")
    country: str = Field(default="US", description="Country code")
    
    class Meta:
        key = "address"
        name = "Address"
        desc = "Collects physical address information"
        table_name = "elem_address"


class PhoneNumberElement(ElementModel):
    """Phone number element with type classification."""
    phone_number: str = Field(description="Phone number")
    country_code: str = Field(default="+1", description="Country dialing code")
    phone_type: str = Field(default="mobile", description="Phone type (mobile, home, work)")
    is_primary: bool = Field(default=False, description="Is this the primary phone")
    
    class Meta:
        key = "phone-number"
        name = "Phone Number"
        desc = "Collects phone number with type classification"
        table_name = "elem_phone_number"


class EmailElement(ElementModel):
    """Email address element."""
    email: str = Field(description="Email address")
    email_type: str = Field(default="personal", description="Email type (personal, work)")
    is_primary: bool = Field(default=False, description="Is this the primary email")
    
    class Meta:
        key = "email"
        name = "Email Address"
        desc = "Collects email address information"
        table_name = "elem_email"


# ============================================================================
# Form Input Elements
# ============================================================================

class TextFieldElement(ElementModel):
    """Single-line text input field."""
    value: str = Field(default="", description="Text value")
    placeholder: Optional[str] = Field(default=None, description="Placeholder text")
    max_length: Optional[int] = Field(default=None, description="Maximum character length")
    min_length: Optional[int] = Field(default=None, description="Minimum character length")
    pattern: Optional[str] = Field(default=None, description="Validation regex pattern")
    
    class Meta:
        key = "text-field"
        name = "Text Field"
        desc = "Single-line text input field"
        table_name = "elem_text_field"


class TextAreaElement(ElementModel):
    """Multi-line text input field."""
    value: str = Field(default="", description="Text value")
    placeholder: Optional[str] = Field(default=None, description="Placeholder text")
    max_length: Optional[int] = Field(default=None, description="Maximum character length")
    rows: int = Field(default=4, description="Number of visible text rows")
    
    class Meta:
        key = "text-area"
        name = "Text Area"
        desc = "Multi-line text input field"
        table_name = "elem_text_area"


class NumberFieldElement(ElementModel):
    """Numeric input field with optional bounds."""
    value: Optional[float] = Field(default=None, description="Numeric value")
    min_value: Optional[float] = Field(default=None, description="Minimum allowed value")
    max_value: Optional[float] = Field(default=None, description="Maximum allowed value")
    step: Optional[float] = Field(default=1.0, description="Step increment")
    decimal_places: Optional[int] = Field(default=None, description="Number of decimal places")
    
    class Meta:
        key = "number-field"
        name = "Number Field"
        desc = "Numeric input field with optional bounds"
        table_name = "elem_number_field"


class DateFieldElement(ElementModel):
    """Date input field."""
    value: Optional[date] = Field(default=None, description="Selected date")
    min_date: Optional[date] = Field(default=None, description="Minimum selectable date")
    max_date: Optional[date] = Field(default=None, description="Maximum selectable date")
    format: str = Field(default="YYYY-MM-DD", description="Date format string")
    
    class Meta:
        key = "date-field"
        name = "Date Field"
        desc = "Date picker input field"
        table_name = "elem_date_field"


class SelectFieldElement(ElementModel):
    """Dropdown select field."""
    value: Optional[str] = Field(default=None, description="Selected value")
    options: List[dict] = Field(default_factory=list, description="List of {value, label} options")
    placeholder: Optional[str] = Field(default=None, description="Placeholder text")
    allow_empty: bool = Field(default=True, description="Allow empty selection")
    
    class Meta:
        key = "select-field"
        name = "Select Field"
        desc = "Dropdown select field"
        table_name = "elem_select_field"


class CheckboxElement(ElementModel):
    """Checkbox input element."""
    checked: bool = Field(default=False, description="Whether the checkbox is checked")
    label: str = Field(default="", description="Checkbox label text")
    
    class Meta:
        key = "checkbox"
        name = "Checkbox"
        desc = "Single checkbox input"
        table_name = "elem_checkbox"


class RadioGroupElement(ElementModel):
    """Radio button group element."""
    value: Optional[str] = Field(default=None, description="Selected option value")
    options: List[dict] = Field(default_factory=list, description="List of {value, label} options")
    layout: str = Field(default="vertical", description="Layout direction (vertical, horizontal)")
    
    class Meta:
        key = "radio-group"
        name = "Radio Group"
        desc = "Radio button group for single selection"
        table_name = "elem_radio_group"


# ============================================================================
# File Upload Elements
# ============================================================================

class FileUploadElement(ElementModel):
    """File upload element."""
    file_id: Optional[str] = Field(default=None, description="Uploaded file ID")
    file_name: Optional[str] = Field(default=None, description="Original file name")
    file_size: Optional[int] = Field(default=None, description="File size in bytes")
    mime_type: Optional[str] = Field(default=None, description="MIME type of the file")
    allowed_types: List[str] = Field(default_factory=list, description="Allowed MIME types")
    max_size_mb: float = Field(default=10.0, description="Maximum file size in MB")
    
    class Meta:
        key = "file-upload"
        name = "File Upload"
        desc = "File upload input"
        table_name = "elem_file_upload"


class ImageUploadElement(ElementModel):
    """Image upload element with preview support."""
    image_id: Optional[str] = Field(default=None, description="Uploaded image ID")
    image_url: Optional[str] = Field(default=None, description="Image URL for preview")
    file_name: Optional[str] = Field(default=None, description="Original file name")
    width: Optional[int] = Field(default=None, description="Image width in pixels")
    height: Optional[int] = Field(default=None, description="Image height in pixels")
    max_size_mb: float = Field(default=5.0, description="Maximum file size in MB")
    
    class Meta:
        key = "image-upload"
        name = "Image Upload"
        desc = "Image upload with preview"
        table_name = "elem_image_upload"


# ============================================================================
# Special Elements
# ============================================================================

class SignatureElement(ElementModel):
    """Digital signature capture element."""
    signature_data: Optional[str] = Field(default=None, description="Base64 encoded signature image")
    signed_at: Optional[str] = Field(default=None, description="ISO timestamp when signed")
    signer_name: Optional[str] = Field(default=None, description="Name of the signer")
    
    class Meta:
        key = "signature"
        name = "Signature"
        desc = "Digital signature capture"
        table_name = "elem_signature"


class RatingElement(ElementModel):
    """Star rating element."""
    value: Optional[int] = Field(default=None, description="Selected rating value")
    max_value: int = Field(default=5, description="Maximum rating value")
    allow_half: bool = Field(default=False, description="Allow half-star ratings")
    
    class Meta:
        key = "rating"
        name = "Rating"
        desc = "Star rating input"
        table_name = "elem_rating"
