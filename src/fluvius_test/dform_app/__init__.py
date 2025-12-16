"""
DForm Test App - Sample Element Models, Form Models, and Document Templates

This module contains sample ElementModel definitions, FormModel definitions,
and DocumentTemplate definitions for testing the DForm system.

Usage:
    # Import to register element models and form models
    import fluvius_test.dform_app
    
    # Import specific elements
    from fluvius_test.dform_app import PersonalInfoElement, AddressElement
    
    # Import specific forms
    from fluvius_test.dform_app import ApplicantInfoForm, EmploymentDetailsForm
    
    # Import templates
    from fluvius_test.dform_app import LoanApplicationTemplate, TEMPLATES
"""

# Element Models
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

# Form Models
from .forms import (
    # Loan Application Forms
    ApplicantInfoForm,
    EmploymentDetailsForm,
    LoanRequestForm,
    AuthorizationForm,
    
    # Customer Onboarding Forms
    AccountInfoForm,
    AddressesForm,
    PreferencesForm,
    
    # Employee Information Forms
    EmployeePersonalForm,
    EmergencyContactForm,
    DocumentsForm,
    
    # Feedback Survey Forms
    OverallRatingForm,
    ServiceRatingsForm,
    CommentsForm,
    ContactOptionalForm,
    
    # Form collections
    LOAN_APPLICATION_FORMS,
    CUSTOMER_ONBOARDING_FORMS,
    EMPLOYEE_INFORMATION_FORMS,
    FEEDBACK_SURVEY_FORMS,
    ALL_FORMS,
)

# Document Templates
from .templates import (
    LoanApplicationTemplate,
    CustomerOnboardingTemplate,
    EmployeeInformationTemplate,
    FeedbackSurveyTemplate,
    TEMPLATES,
)

__all__ = [
    # Elements
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
    
    # Loan Application Forms
    "ApplicantInfoForm",
    "EmploymentDetailsForm",
    "LoanRequestForm",
    "AuthorizationForm",
    
    # Customer Onboarding Forms
    "AccountInfoForm",
    "AddressesForm",
    "PreferencesForm",
    
    # Employee Information Forms
    "EmployeePersonalForm",
    "EmergencyContactForm",
    "DocumentsForm",
    
    # Feedback Survey Forms
    "OverallRatingForm",
    "ServiceRatingsForm",
    "CommentsForm",
    "ContactOptionalForm",
    
    # Form collections
    "LOAN_APPLICATION_FORMS",
    "CUSTOMER_ONBOARDING_FORMS",
    "EMPLOYEE_INFORMATION_FORMS",
    "FEEDBACK_SURVEY_FORMS",
    "ALL_FORMS",
    
    # Templates
    "LoanApplicationTemplate",
    "CustomerOnboardingTemplate",
    "EmployeeInformationTemplate",
    "FeedbackSurveyTemplate",
    "TEMPLATES",
]
