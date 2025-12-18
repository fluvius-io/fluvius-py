"""
Sample Document Templates for DForm Testing

This module provides sample DocumentTemplate definitions that demonstrate
how to structure documents with sections and form references.

Forms are referenced via FormNode using their registered form_key.
"""
from fluvius.dform.document import (
    DocumentTemplate,
    DocumentSection,
    ContentNode,
    FormNode,
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
        ContentNode(
            title="Loan Application",
            content="Complete this form to apply for a loan. All fields marked with * are required.",
            ctype="header"
        ),

        DocumentSection(
            title="Section 1: Personal Information",
            children=[
                ContentNode(
                    title="Instructions",
                    content="Please provide your personal information as it appears on your government-issued ID.",
                    ctype="text"
                ),
                FormNode(form_key="applicant-info"),
            ]
        ),

        DocumentSection(
            title="Section 2: Employment Information",
            children=[
                ContentNode(
                    title="Employment Verification",
                    content="Provide details about your current employment status.",
                    ctype="text"
                ),
                FormNode(form_key="employment-details"),
            ]
        ),

        DocumentSection(
            title="Section 3: Loan Details",
            children=[
                FormNode(form_key="loan-request"),
            ]
        ),

        DocumentSection(
            title="Section 4: Authorization",
            children=[
                ContentNode(
                    title="Authorization Statement",
                    content="By signing below, I authorize the lender to verify my information and pull my credit report.",
                    ctype="text"
                ),
                FormNode(form_key="authorization"),
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
        ContentNode(
            title="Welcome to Our Service",
            content="Please complete the following information to set up your account.",
            ctype="header"
        ),

        DocumentSection(
            title="Account Information",
            children=[
                FormNode(form_key="account-info"),
            ]
        ),

        DocumentSection(
            title="Address Information",
            children=[
                FormNode(form_key="addresses"),
            ]
        ),

        DocumentSection(
            title="Preferences",
            children=[
                FormNode(form_key="preferences"),
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
        ContentNode(
            title="Employee Information Form",
            content="HR Department - Confidential",
            ctype="header"
        ),

        DocumentSection(
            title="Personal Details",
            children=[
                FormNode(form_key="employee-personal"),
            ]
        ),

        DocumentSection(
            title="Emergency Contact",
            children=[
                FormNode(form_key="emergency-contact"),
            ]
        ),

        DocumentSection(
            title="Documents",
            children=[
                FormNode(form_key="documents"),
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
        ContentNode(
            title="We Value Your Feedback",
            content="Please take a moment to share your experience with us.",
            ctype="header"
        ),

        DocumentSection(
            title="Overall Experience",
            children=[
                FormNode(form_key="overall-rating"),
            ]
        ),

        DocumentSection(
            title="Detailed Feedback",
            children=[
                FormNode(form_key="service-ratings"),
                FormNode(form_key="comments"),
            ]
        ),

        DocumentSection(
            title="Contact Information (Optional)",
            children=[
                ContentNode(
                    title="Follow-up",
                    content="If you'd like us to follow up on your feedback, please provide your contact information.",
                    ctype="text"
                ),
                FormNode(form_key="contact-optional"),
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
