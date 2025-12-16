"""
Sample Document Templates for DForm Testing

This module provides sample DocumentTemplate definitions that demonstrate
how to structure documents with sections and form references.

Forms are referenced via FormRef using their registered form_key.
"""
from fluvius.dform.document import (
    DocumentTemplate,
    DocumentSection,
    TextNode,
    HeaderNode,
    FormRef,
)

# Import forms module to ensure all FormModels are registered
from . import forms as _  # noqa: F401


# ============================================================================
# Loan Application Template
# ============================================================================

LoanApplicationTemplate = DocumentTemplate(
    template_key="loan-application",
    title="Loan Application Form",
    children=[
        HeaderNode(
            header="Loan Application",
            content="Complete this form to apply for a loan. All fields marked with * are required."
        ),
        
        DocumentSection(
            title="Section 1: Personal Information",
            children=[
                TextNode(
                    title="Instructions",
                    content="Please provide your personal information as it appears on your government-issued ID."
                ),
                FormRef(form_key="applicant-info"),
            ]
        ),
        
        DocumentSection(
            title="Section 2: Employment Information",
            children=[
                TextNode(
                    title="Employment Verification",
                    content="Provide details about your current employment status."
                ),
                FormRef(form_key="employment-details"),
            ]
        ),
        
        DocumentSection(
            title="Section 3: Loan Details",
            children=[
                FormRef(form_key="loan-request"),
            ]
        ),
        
        DocumentSection(
            title="Section 4: Authorization",
            children=[
                TextNode(
                    title="Authorization Statement",
                    content="By signing below, I authorize the lender to verify my information and pull my credit report."
                ),
                FormRef(form_key="authorization"),
            ]
        ),
    ]
)


# ============================================================================
# Customer Onboarding Template
# ============================================================================

CustomerOnboardingTemplate = DocumentTemplate(
    template_key="customer-onboarding",
    title="Customer Onboarding Form",
    children=[
        HeaderNode(
            header="Welcome to Our Service",
            content="Please complete the following information to set up your account."
        ),
        
        DocumentSection(
            title="Account Information",
            children=[
                FormRef(form_key="account-info"),
            ]
        ),
        
        DocumentSection(
            title="Address Information",
            children=[
                FormRef(form_key="addresses"),
            ]
        ),
        
        DocumentSection(
            title="Preferences",
            children=[
                FormRef(form_key="preferences"),
            ]
        ),
    ]
)


# ============================================================================
# Employee Information Template
# ============================================================================

EmployeeInformationTemplate = DocumentTemplate(
    template_key="employee-information",
    title="Employee Information Form",
    children=[
        HeaderNode(
            header="Employee Information Form",
            content="HR Department - Confidential"
        ),
        
        DocumentSection(
            title="Personal Details",
            children=[
                FormRef(form_key="employee-personal"),
            ]
        ),
        
        DocumentSection(
            title="Emergency Contact",
            children=[
                FormRef(form_key="emergency-contact"),
            ]
        ),
        
        DocumentSection(
            title="Documents",
            children=[
                FormRef(form_key="documents"),
            ]
        ),
    ]
)


# ============================================================================
# Feedback Survey Template
# ============================================================================

FeedbackSurveyTemplate = DocumentTemplate(
    template_key="feedback-survey",
    title="Customer Feedback Survey",
    children=[
        HeaderNode(
            header="We Value Your Feedback",
            content="Please take a moment to share your experience with us."
        ),
        
        DocumentSection(
            title="Overall Experience",
            children=[
                FormRef(form_key="overall-rating"),
            ]
        ),
        
        DocumentSection(
            title="Detailed Feedback",
            children=[
                FormRef(form_key="service-ratings"),
                FormRef(form_key="comments"),
            ]
        ),
        
        DocumentSection(
            title="Contact Information (Optional)",
            children=[
                TextNode(
                    title="Follow-up",
                    content="If you'd like us to follow up on your feedback, please provide your contact information."
                ),
                FormRef(form_key="contact-optional"),
            ]
        ),
    ]
)


# ============================================================================
# Export all templates
# ============================================================================

TEMPLATES = [
    LoanApplicationTemplate,
    CustomerOnboardingTemplate,
    EmployeeInformationTemplate,
    FeedbackSurveyTemplate,
]

__all__ = [
    "LoanApplicationTemplate",
    "CustomerOnboardingTemplate", 
    "EmployeeInformationTemplate",
    "FeedbackSurveyTemplate",
    "TEMPLATES",
]
