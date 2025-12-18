"""
Sample Form Definitions for DForm Testing

This module provides reusable FormModel definitions that can be referenced
in document templates via FormRef. Forms are defined as classes that
inherit from FormModel and register automatically.
"""
from fluvius.dform.form import FormModel, FormElement


# ============================================================================
# Loan Application Forms
# ============================================================================

class ApplicantInfoForm(FormModel):
    """Primary applicant personal details"""
    personal_info: FormElement("personal-info", param={"required": True})
    address: FormElement("address", param={"required": True, "label": "Current Address"})
    phone: FormElement("phone-number", param={"required": True})
    email: FormElement("email", param={"required": True})

    class Meta:
        key = "applicant-info"
        name = "Applicant Information"
        desc = "Primary applicant personal details"
        header = "Primary Applicant"
        footer = "All information will be verified."


class EmploymentDetailsForm(FormModel):
    """Current employment information"""
    employer_name: FormElement("text-field", param={"label": "Employer Name", "required": True})
    job_title: FormElement("text-field", param={"label": "Job Title", "required": True})
    employer_address: FormElement("address", param={"label": "Employer Address"})
    employer_phone: FormElement("phone-number", param={"label": "Employer Phone"})
    annual_income: FormElement("number-field", param={"label": "Annual Income ($)", "required": True, "min": 0})
    employment_start: FormElement("date-field", param={"label": "Start Date", "required": True})

    class Meta:
        key = "employment-details"
        name = "Employment Details"
        desc = "Current employment information"
        header = "Employment Information"
        footer = "Employment will be verified with your employer."


class LoanRequestForm(FormModel):
    """Loan request details"""
    loan_amount: FormElement(
        "number-field",
        param={"label": "Requested Loan Amount ($)", "required": True, "min": 1000}
    )
    loan_purpose: FormElement(
        "select-field",
        param={
            "label": "Loan Purpose",
            "required": True,
            "options": [
                {"value": "home", "label": "Home Purchase"},
                {"value": "auto", "label": "Auto Loan"},
                {"value": "personal", "label": "Personal Loan"},
                {"value": "business", "label": "Business Loan"},
                {"value": "education", "label": "Education Loan"},
            ]
        }
    )
    loan_term: FormElement(
        "select-field",
        param={
            "label": "Loan Term",
            "required": True,
            "options": [
                {"value": "12", "label": "12 Months"},
                {"value": "24", "label": "24 Months"},
                {"value": "36", "label": "36 Months"},
                {"value": "48", "label": "48 Months"},
                {"value": "60", "label": "60 Months"},
            ]
        }
    )

    class Meta:
        key = "loan-request"
        name = "Loan Request"
        desc = "Specify your loan requirements"
        header = "Loan Information"


class AuthorizationForm(FormModel):
    """Applicant authorization and signature"""
    consent: FormElement(
        "checkbox",
        param={"label": "I agree to the terms and conditions", "required": True}
    )
    signature: FormElement("signature", param={"required": True})

    class Meta:
        key = "authorization"
        name = "Authorization"
        desc = "Applicant authorization"


# ============================================================================
# Customer Onboarding Forms
# ============================================================================

class AccountInfoForm(FormModel):
    """Basic account information"""
    personal: FormElement("personal-info", param={"required": True})
    email: FormElement("email", param={"required": True, "is_primary": True})
    phone: FormElement("phone-number", param={"required": True})

    class Meta:
        key = "account-info"
        name = "Account Information"
        desc = "Your account details"
        header = "Personal Details"


class AddressesForm(FormModel):
    """Contact addresses"""
    billing_address: FormElement("address", param={"label": "Billing Address", "required": True})
    same_as_billing: FormElement("checkbox", param={"label": "Shipping address same as billing"})
    shipping_address: FormElement("address", param={"label": "Shipping Address"})

    class Meta:
        key = "addresses"
        name = "Addresses"
        desc = "Your contact addresses"


class PreferencesForm(FormModel):
    """Communication preferences"""
    contact_method: FormElement(
        "radio-group",
        param={
            "label": "Preferred Contact Method",
            "options": [
                {"value": "email", "label": "Email"},
                {"value": "phone", "label": "Phone"},
                {"value": "sms", "label": "SMS"},
            ]
        }
    )
    newsletter: FormElement("checkbox", param={"label": "Subscribe to newsletter"})
    promotions: FormElement("checkbox", param={"label": "Receive promotional offers"})

    class Meta:
        key = "preferences"
        name = "Communication Preferences"
        desc = "How would you like us to contact you?"


# ============================================================================
# Employee Information Forms
# ============================================================================

class EmployeePersonalForm(FormModel):
    """Employee personal information"""
    personal: FormElement("personal-info", param={"required": True})
    address: FormElement("address", param={"required": True})
    phone: FormElement("phone-number", param={"required": True})
    email: FormElement("email", param={"required": True, "email_type": "work"})
    personal_email: FormElement("email", param={"label": "Personal Email", "email_type": "personal"})

    class Meta:
        key = "employee-personal"
        name = "Employee Personal Information"
        desc = "Basic employee information"


class EmergencyContactForm(FormModel):
    """Emergency contact information"""
    contact_name: FormElement("text-field", param={"label": "Contact Name", "required": True})
    relationship: FormElement(
        "select-field",
        param={
            "label": "Relationship",
            "required": True,
            "options": [
                {"value": "spouse", "label": "Spouse"},
                {"value": "parent", "label": "Parent"},
                {"value": "sibling", "label": "Sibling"},
                {"value": "friend", "label": "Friend"},
                {"value": "other", "label": "Other"},
            ]
        }
    )
    contact_phone: FormElement("phone-number", param={"label": "Phone Number", "required": True})

    class Meta:
        key = "emergency-contact"
        name = "Emergency Contact Information"
        desc = "Person to contact in case of emergency"


class DocumentsForm(FormModel):
    """Required documents upload"""
    id_document: FormElement(
        "file-upload",
        param={
            "label": "Government ID",
            "required": True,
            "allowed_types": ["application/pdf", "image/jpeg", "image/png"]
        }
    )
    photo: FormElement("image-upload", param={"label": "Profile Photo", "required": True})

    class Meta:
        key = "documents"
        name = "Required Documents"
        desc = "Upload required employment documents"
        footer = "Accepted formats: PDF, JPG, PNG"


# ============================================================================
# Feedback Survey Forms
# ============================================================================

class OverallRatingForm(FormModel):
    """Overall experience rating"""
    overall_rating: FormElement(
        "rating",
        param={"label": "Overall Satisfaction", "required": True, "max_value": 5}
    )
    recommend: FormElement(
        "radio-group",
        param={
            "label": "Would you recommend us to others?",
            "required": True,
            "options": [
                {"value": "yes", "label": "Yes"},
                {"value": "maybe", "label": "Maybe"},
                {"value": "no", "label": "No"},
            ]
        }
    )

    class Meta:
        key = "overall-rating"
        name = "Overall Rating"
        desc = "Rate your overall experience"


class ServiceRatingsForm(FormModel):
    """Service aspect ratings"""
    quality_rating: FormElement("rating", param={"label": "Product/Service Quality", "max_value": 5})
    support_rating: FormElement("rating", param={"label": "Customer Support", "max_value": 5})
    value_rating: FormElement("rating", param={"label": "Value for Money", "max_value": 5})

    class Meta:
        key = "service-ratings"
        name = "Service Ratings"
        desc = "Rate individual aspects of our service"


class CommentsForm(FormModel):
    """Free-form comments"""
    liked: FormElement("text-area", param={"label": "What did you like?", "rows": 3})
    improvements: FormElement("text-area", param={"label": "What could we improve?", "rows": 3})
    additional_comments: FormElement("text-area", param={"label": "Additional Comments", "rows": 4})

    class Meta:
        key = "comments"
        name = "Comments"
        desc = "Share your thoughts"


class ContactOptionalForm(FormModel):
    """Optional contact information for follow-up"""
    name: FormElement("text-field", param={"label": "Name"})
    email: FormElement("email", param={"label": "Email"})
    can_contact: FormElement("checkbox", param={"label": "You may contact me about my feedback"})

    class Meta:
        key = "contact-optional"
        name = "Contact Details"
        desc = "Optional contact information"


# ============================================================================
# Export all forms
# ============================================================================

# Loan Application Forms
LOAN_APPLICATION_FORMS = [
    ApplicantInfoForm,
    EmploymentDetailsForm,
    LoanRequestForm,
    AuthorizationForm,
]

# Customer Onboarding Forms
CUSTOMER_ONBOARDING_FORMS = [
    AccountInfoForm,
    AddressesForm,
    PreferencesForm,
]

# Employee Information Forms
EMPLOYEE_INFORMATION_FORMS = [
    EmployeePersonalForm,
    EmergencyContactForm,
    DocumentsForm,
]

# Feedback Survey Forms
FEEDBACK_SURVEY_FORMS = [
    OverallRatingForm,
    ServiceRatingsForm,
    CommentsForm,
    ContactOptionalForm,
]

# All forms
ALL_FORMS = (
    LOAN_APPLICATION_FORMS +
    CUSTOMER_ONBOARDING_FORMS +
    EMPLOYEE_INFORMATION_FORMS +
    FEEDBACK_SURVEY_FORMS
)

__all__ = [
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
]
