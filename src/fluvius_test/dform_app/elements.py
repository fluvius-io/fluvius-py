"""
Sample Element Models for DForm Testing

This module provides a comprehensive set of ElementModel definitions
that can be used for testing the DForm element schema system.
"""
from typing import Optional, List
from datetime import date
from pydantic import Field, EmailStr
from enum import Enum

from fluvius.dform.element import DataElementModel


# ============================================================================
# Personal Information Elements
# ============================================================================

class PersonalInfoElement(DataElementModel):
    """Personal information element for collecting name, DOB, etc."""
    first_name: str = Field(description="First name")
    last_name: str = Field(description="Last name")
    middle_name: Optional[str] = Field(default=None, description="Middle name")
    date_of_birth: Optional[date] = Field(default=None, description="Date of birth")
    gender: Optional[str] = Field(default=None, description="Gender")
    
    class Meta:
        key = "personal-info"
        title = "Personal Information"
        description = "Collects personal information including name and date of birth"
        table_name = "dfe_personal_info"


class AddressElement(DataElementModel):
    """Address element for collecting physical addresses."""
    street_line1: str = Field(description="Street address line 1")
    street_line2: Optional[str] = Field(default=None, description="Street address line 2")
    city: str = Field(description="City")
    state: str = Field(description="State/Province")
    postal_code: str = Field(description="Postal/ZIP code")
    country: str = Field(default="US", description="Country code")
    
    class Meta:
        key = "address"
        title = "Address"
        description = "Collects physical address information"
        table_name = "dfe_address"


class PhoneNumberElement(DataElementModel):
    """Phone number element with type classification."""
    phone_number: str = Field(description="Phone number")
    country_code: str = Field(default="+1", description="Country dialing code")
    phone_type: str = Field(default="mobile", description="Phone type (mobile, home, work)")
    is_primary: bool = Field(default=False, description="Is this the primary phone")
    
    class Meta:
        key = "phone-number"
        title = "Phone Number"
        description = "Collects phone number with type classification"
        table_name = "dfe_phone_number"


class EmailElement(DataElementModel):
    """Email address element."""
    email: str = Field(description="Email address")
    email_type: str = Field(default="personal", description="Email type (personal, work)")
    is_primary: bool = Field(default=False, description="Is this the primary email")
    
    class Meta:
        key = "email"
        title = "Email Address"
        description = "Collects email address information"
        table_name = "dfe_email"


# ============================================================================
# Form Input Elements
# ============================================================================

class TextFieldElement(DataElementModel):
    """Single-line text input field."""
    value: str = Field(default="", description="Text value")
    placeholder: Optional[str] = Field(default=None, description="Placeholder text")
    max_length: Optional[int] = Field(default=None, description="Maximum character length")
    min_length: Optional[int] = Field(default=None, description="Minimum character length")
    pattern: Optional[str] = Field(default=None, description="Validation regex pattern")
    
    class Meta:
        key = "text-field"
        title = "Text Field"
        description = "Single-line text input field"
        table_name = "dfe_text_field"


class TextAreaElement(DataElementModel):
    """Multi-line text input field."""
    value: str = Field(default="", description="Text value")
    placeholder: Optional[str] = Field(default=None, description="Placeholder text")
    max_length: Optional[int] = Field(default=None, description="Maximum character length")
    rows: int = Field(default=4, description="Number of visible text rows")
    
    class Meta:
        key = "text-area"
        title = "Text Area"
        description = "Multi-line text input field"
        table_name = "dfe_text_area"


class NumberFieldElement(DataElementModel):
    """Numeric input field with optional bounds."""
    value: Optional[float] = Field(default=None, description="Numeric value")
    min_value: Optional[float] = Field(default=None, description="Minimum allowed value")
    max_value: Optional[float] = Field(default=None, description="Maximum allowed value")
    step: Optional[float] = Field(default=1.0, description="Step increment")
    decimal_places: Optional[int] = Field(default=None, description="Number of decimal places")
    
    class Meta:
        key = "number-field"
        title = "Number Field"
        description = "Numeric input field with optional bounds"
        table_name = "dfe_number_field"


class DateFieldElement(DataElementModel):
    """Date input field."""
    value: Optional[date] = Field(default=None, description="Selected date")
    min_date: Optional[date] = Field(default=None, description="Minimum selectable date")
    max_date: Optional[date] = Field(default=None, description="Maximum selectable date")
    format: str = Field(default="YYYY-MM-DD", description="Date format string")
    
    class Meta:
        key = "date-field"
        title = "Date Field"
        description = "Date picker input field"
        table_name = "dfe_date_field"


class SelectFieldElement(DataElementModel):
    """Dropdown select field."""
    value: Optional[str] = Field(default=None, description="Selected value")
    options: List[dict] = Field(default_factory=list, description="List of {value, label} options")
    placeholder: Optional[str] = Field(default=None, description="Placeholder text")
    allow_empty: bool = Field(default=True, description="Allow empty selection")
    
    class Meta:
        key = "select-field"
        title = "Select Field"
        description = "Dropdown select field"
        table_name = "dfe_select_field"


class CheckboxElement(DataElementModel):
    """Checkbox input element."""
    checked: bool = Field(default=False, description="Whether the checkbox is checked")
    label: str = Field(default="", description="Checkbox label text")
    
    class Meta:
        key = "checkbox"
        title = "Checkbox"
        description = "Single checkbox input"
        table_name = "dfe_checkbox"


class RadioGroupElement(DataElementModel):
    """Radio button group element."""
    value: Optional[str] = Field(default=None, description="Selected option value")
    options: List[dict] = Field(default_factory=list, description="List of {value, label} options")
    layout: str = Field(default="vertical", description="Layout direction (vertical, horizontal)")
    
    class Meta:
        key = "radio-group"
        title = "Radio Group"
        description = "Radio button group for single selection"
        table_name = "dfe_radio_group"


# ============================================================================
# File Upload Elements
# ============================================================================

class FileUploadElement(DataElementModel):
    """File upload element."""
    file_id: Optional[str] = Field(default=None, description="Uploaded file ID")
    file_name: Optional[str] = Field(default=None, description="Original file name")
    file_size: Optional[int] = Field(default=None, description="File size in bytes")
    mime_type: Optional[str] = Field(default=None, description="MIME type of the file")
    allowed_types: List[str] = Field(default_factory=list, description="Allowed MIME types")
    max_size_mb: float = Field(default=10.0, description="Maximum file size in MB")
    
    class Meta:
        key = "file-upload"
        title = "File Upload"
        description = "File upload input"
        table_name = "dfe_file_upload"


class ImageUploadElement(DataElementModel):
    """Image upload element with preview support."""
    image_id: Optional[str] = Field(default=None, description="Uploaded image ID")
    image_url: Optional[str] = Field(default=None, description="Image URL for preview")
    file_name: Optional[str] = Field(default=None, description="Original file name")
    width: Optional[int] = Field(default=None, description="Image width in pixels")
    height: Optional[int] = Field(default=None, description="Image height in pixels")
    max_size_mb: float = Field(default=5.0, description="Maximum file size in MB")
    
    class Meta:
        key = "image-upload"
        title = "Image Upload"
        description = "Image upload with preview"
        table_name = "dfe_image_upload"


# ============================================================================
# Special Elements
# ============================================================================

class SignatureElement(DataElementModel):
    """Digital signature capture element."""
    signature_data: Optional[str] = Field(default=None, description="Base64 encoded signature image")
    signed_at: Optional[str] = Field(default=None, description="ISO timestamp when signed")
    signer_name: Optional[str] = Field(default=None, description="Name of the signer")
    
    class Meta:
        key = "signature"
        title = "Signature"
        description = "Digital signature capture"
        table_name = "dfe_signature"


class RatingElement(DataElementModel):
    """Star rating element."""
    value: Optional[int] = Field(default=None, description="Selected rating value")
    max_value: int = Field(default=5, description="Maximum rating value")
    allow_half: bool = Field(default=False, description="Allow half-star ratings")
    
    class Meta:
        key = "rating"
        title = "Rating"
        description = "Star rating input"
        table_name = "dfe_rating"
