"""
Loan Application Process Workflow

This module implements a complete loan application workflow from pre-qualification
through closing, following industry-standard mortgage lending practices.
"""

from fluvius.data import UUID_GENF, logger
from fluvius.navis import Workflow, Stage, Step, Role, connect, transition, FINISH_STATE, BEGIN_STATE
from typing import Optional
from types import SimpleNamespace


class LoanApplicationProcess(Workflow):
    """
    Complete loan application workflow covering all stages from pre-qualification to closing.
    
    The workflow follows these major stages:
    1. PRE-QUALIFICATION - Initial borrower assessment with soft credit pull
    2. PRE-APPROVAL - Formal approval with hard credit pull and AUS
    3. PURCHASE OFFER - Property identification and offer submission
    4. LOAN APPLICATION SUBMISSION - Official application with documentation
    5. UNDERWRITING SUBMISSION - Full underwriting and approval process
    6. CLOSING - Final disclosure, funding, and closing
    """

    class Meta:
        title = "Loan Application Process"
        revision = 1
        namespace = "lending"

    # Define Roles
    LoanOfficer = Role(title="Loan Officer")
    Borrower = Role(title="Borrower")
    Processor = Role(title="Processor")
    Underwriter = Role(title="Underwriter")
    ClosingAgent = Role(title="Closing Agent")

    # Define Stages
    Stage01_PreQualification = Stage('PRE-QUALIFICATION', order=1, desc="Initial borrower assessment and soft credit pull")
    Stage02_PreApproval = Stage('PRE-APPROVAL', order=2, desc="Formal pre-approval with hard credit pull")
    Stage03_PurchaseOffer = Stage('PURCHASE OFFER', order=3, desc="Property identification and purchase agreement")
    Stage04_LoanSubmission = Stage('OFFICIAL LOAN APPLICATION SUBMISSION', order=4, desc="Official application submission with documentation")
    Stage05_Underwriting = Stage('UNDERWRITING SUBMISSION', order=5, desc="Underwriting review and conditional approval")
    Stage06_Closing = Stage('CLOSING', order=6, desc="Final closing and funding")

    # ==================================================================================
    # STAGE 01: PRE-QUALIFICATION STEPS
    # ==================================================================================

    class CollectBasicInformation(Step, name='Collect Basic Information', stage=Stage01_PreQualification):
        """Borrower provides basic information and authorizes soft pull"""
        __states__ = ('PENDING', 'COLLECTING', 'COMPLETED')

        @transition('COLLECTING')
        def start_collection(state, cur_state):
            yield f'Starting basic information collection for borrower'

        @transition('COMPLETED')
        def complete_collection(state, cur_state):
            yield f'Basic information collection completed'

    class TransferToLOS(Step, name='Transfer Input Data to LOS', stage=Stage01_PreQualification):
        """Loan Officer transfers input data into the Loan Origination System"""
        __states__ = ('PENDING', 'TRANSFERRING', 'COMPLETED')

        @transition('TRANSFERRING')
        def start_transfer(state, cur_state):
            yield f'Transferring borrower data to LOS'

        @transition('COMPLETED')
        def complete_transfer(state, cur_state):
            yield f'Data successfully transferred to LOS'

    class RequestSoftPull(Step, name='Request Soft Credit Pull', stage=Stage01_PreQualification):
        """LO requests soft pull from credit bureau"""
        __states__ = ('PENDING', 'REQUESTING', 'RECEIVED', 'COMPLETED')

        @transition('REQUESTING')
        def initiate_request(state, cur_state):
            yield f'Initiating soft credit pull request'

        @transition('RECEIVED')
        def receive_report(state, cur_state):
            yield f'Soft credit report received from bureau'

        @transition('COMPLETED')
        def complete_review(state, cur_state):
            yield f'Soft credit pull review completed'

    class ReviewSoftPull(Step, name='Review Soft Pull Report', stage=Stage01_PreQualification):
        """LO receives and reviews the soft pull report"""
        __states__ = ('PENDING', 'REVIEWING', 'COMPLETED')

        @transition('REVIEWING')
        def start_review(state, cur_state):
            yield f'Starting soft pull report review'

        @transition('COMPLETED')
        def complete_review(state, cur_state):
            yield f'Soft pull report review completed'

    class AssessCreditworthiness(Step, name='Assess Creditworthiness', stage=Stage01_PreQualification):
        """Assess borrower creditworthiness based on soft pull"""
        __states__ = ('PENDING', 'ASSESSING', 'APPROVED', 'DECLINED', 'COMPLETED')

        @transition('ASSESSING')
        def start_assessment(state, cur_state):
            yield f'Starting creditworthiness assessment'

        @transition('APPROVED')
        def approve_credit(state, cur_state):
            yield f'Creditworthiness approved'

        @transition('DECLINED')
        def decline_credit(state, cur_state):
            yield f'Creditworthiness declined'

        @transition('COMPLETED')
        def complete_assessment(state, cur_state):
            yield f'Creditworthiness assessment completed'

    class VerifyIncomeEmployment(Step, name='Verify Income & Employment', stage=Stage01_PreQualification):
        """Verify income and employment consistency"""
        __states__ = ('PENDING', 'VERIFYING', 'VERIFIED', 'NEEDS_CLARIFICATION', 'COMPLETED')

        @transition('VERIFYING')
        def start_verification(state, cur_state):
            yield f'Starting income and employment verification'

        @transition('VERIFIED')
        def mark_verified(state, cur_state):
            yield f'Income and employment verified'

        @transition('NEEDS_CLARIFICATION')
        def request_clarification(state, cur_state):
            yield f'Additional clarification needed for income/employment'

        @transition('COMPLETED')
        def complete_verification(state, cur_state):
            yield f'Income and employment verification completed'

    class DiscussCreditFindings(Step, name='Discuss Credit Findings with Borrower', stage=Stage01_PreQualification):
        """Discuss credit findings with borrower and provide initial consultation"""
        __states__ = ('PENDING', 'SCHEDULED', 'IN_CONSULTATION', 'COMPLETED')

        @transition('SCHEDULED')
        def schedule_consultation(state, cur_state):
            yield f'Consultation scheduled with borrower'

        @transition('IN_CONSULTATION')
        def start_consultation(state, cur_state):
            yield f'Starting credit findings consultation'

        @transition('COMPLETED')
        def complete_consultation(state, cur_state):
            yield f'Credit findings consultation completed'

    # ==================================================================================
    # STAGE 02: PRE-APPROVAL STEPS
    # ==================================================================================

    class DetermineLoanEligibility(Step, name='Determine Loan Eligibility', stage=Stage02_PreApproval):
        """Determine loan eligibility based on pre-qualification results"""
        __states__ = ('PENDING', 'ANALYZING', 'ELIGIBLE', 'NOT_ELIGIBLE', 'COMPLETED')

        @transition('ANALYZING')
        def start_analysis(state, cur_state):
            yield f'Starting loan eligibility analysis'

        @transition('ELIGIBLE')
        def mark_eligible(state, cur_state):
            yield f'Borrower eligible for loan'

        @transition('NOT_ELIGIBLE')
        def mark_not_eligible(state, cur_state):
            yield f'Borrower not eligible for loan'

        @transition('COMPLETED')
        def complete_determination(state, cur_state):
            yield f'Loan eligibility determination completed'

    class ProvidePreQualEstimate(Step, name='Provide Pre-Qualification Estimate', stage=Stage02_PreApproval):
        """Provide pre-qualification estimate to borrower"""
        __states__ = ('PENDING', 'PREPARING', 'SENT', 'COMPLETED')

        @transition('PREPARING')
        def prepare_estimate(state, cur_state):
            yield f'Preparing pre-qualification estimate'

        @transition('SENT')
        def send_estimate(state, cur_state):
            yield f'Pre-qualification estimate sent to borrower'

        @transition('COMPLETED')
        def complete_estimate(state, cur_state):
            yield f'Pre-qualification estimate completed'

    class AddressDocumentationGaps(Step, name='Address Credit or Documentation Gaps', stage=Stage02_PreApproval):
        """Address any credit or documentation gaps identified"""
        __states__ = ('PENDING', 'REVIEWING_GAPS', 'COLLECTING_DOCS', 'RESOLVED', 'COMPLETED')

        @transition('REVIEWING_GAPS')
        def review_gaps(state, cur_state):
            yield f'Reviewing credit and documentation gaps'

        @transition('COLLECTING_DOCS')
        def collect_documents(state, cur_state):
            yield f'Collecting additional documentation'

        @transition('RESOLVED')
        def resolve_gaps(state, cur_state):
            yield f'Documentation gaps resolved'

        @transition('COMPLETED')
        def complete_gap_resolution(state, cur_state):
            yield f'Gap resolution completed'

    class CollectPreApprovalDocuments(Step, name='Collect Documents for Pre-Approval', stage=Stage02_PreApproval):
        """Collect all necessary documents for pre-approval"""
        __states__ = ('PENDING', 'COLLECTING', 'REVIEWING', 'COMPLETE', 'NEEDS_MORE')

        @transition('COLLECTING')
        def start_collection(state, cur_state):
            yield f'Starting pre-approval document collection'

        @transition('REVIEWING')
        def review_documents(state, cur_state):
            yield f'Reviewing submitted documents'

        @transition('COMPLETE')
        def mark_complete(state, cur_state):
            yield f'All pre-approval documents received'

        @transition('NEEDS_MORE')
        def request_more_documents(state, cur_state):
            yield f'Additional documents needed'

    class RunAUS(Step, name='Run AUS with Hard Pull', stage=Stage02_PreApproval):
        """Run Automated Underwriting System (DU or LP) with hard credit pull"""
        __states__ = ('PENDING', 'RUNNING', 'APPROVE_ELIGIBLE', 'REFER', 'COMPLETED')

        @transition('RUNNING')
        def start_aus(state, cur_state):
            yield f'Running AUS (Desktop Underwriter or Loan Prospector)'

        @transition('APPROVE_ELIGIBLE')
        def approve_eligible(state, cur_state):
            yield f'AUS result: Approve/Eligible'

        @transition('REFER')
        def refer_underwriting(state, cur_state):
            yield f'AUS result: Refer to underwriting'

        @transition('COMPLETED')
        def complete_aus(state, cur_state):
            yield f'AUS run completed'

    class IssuePreApprovalLetter(Step, name='Issue Pre-Approval Letter', stage=Stage02_PreApproval):
        """Issue the pre-approval letter to borrower"""
        __states__ = ('PENDING', 'DRAFTING', 'REVIEWING', 'ISSUED', 'COMPLETED')

        @transition('DRAFTING')
        def draft_letter(state, cur_state):
            yield f'Drafting pre-approval letter'

        @transition('REVIEWING')
        def review_letter(state, cur_state):
            yield f'Reviewing pre-approval letter'

        @transition('ISSUED')
        def issue_letter(state, cur_state):
            yield f'Pre-approval letter issued to borrower'

        @transition('COMPLETED')
        def complete_letter(state, cur_state):
            yield f'Pre-approval letter process completed'

    # ==================================================================================
    # STAGE 03: PURCHASE OFFER STEPS
    # ==================================================================================

    class CollectPropertyInformation(Step, name='Collect Property Information', stage=Stage03_PurchaseOffer):
        """Collect information about the property to be purchased"""
        __states__ = ('PENDING', 'COLLECTING', 'REVIEWING', 'COMPLETED')

        @transition('COLLECTING')
        def start_collection(state, cur_state):
            yield f'Starting property information collection'

        @transition('REVIEWING')
        def review_property(state, cur_state):
            yield f'Reviewing property information'

        @transition('COMPLETED')
        def complete_collection(state, cur_state):
            yield f'Property information collection completed'

    class SubmitPurchaseOffer(Step, name='Submit Purchase Offer', stage=Stage03_PurchaseOffer):
        """Submit purchase offer for the property"""
        __states__ = ('PENDING', 'DRAFTING', 'SUBMITTED', 'NEGOTIATING', 'ACCEPTED', 'REJECTED', 'COMPLETED')

        @transition('DRAFTING')
        def draft_offer(state, cur_state):
            yield f'Drafting purchase offer'

        @transition('SUBMITTED')
        def submit_offer(state, cur_state):
            yield f'Purchase offer submitted'

        @transition('NEGOTIATING')
        def negotiate_offer(state, cur_state):
            yield f'Negotiating purchase offer terms'

        @transition('ACCEPTED')
        def accept_offer(state, cur_state):
            yield f'Purchase offer accepted'

        @transition('REJECTED')
        def reject_offer(state, cur_state):
            yield f'Purchase offer rejected'

        @transition('COMPLETED')
        def complete_offer(state, cur_state):
            yield f'Purchase offer process completed'

    class ExecutePurchaseAgreement(Step, name='Execute Purchase Agreement', stage=Stage03_PurchaseOffer):
        """Execute and sign the purchase agreement"""
        __states__ = ('PENDING', 'DRAFTING', 'REVIEWING', 'SIGNED', 'COMPLETED')

        @transition('DRAFTING')
        def draft_agreement(state, cur_state):
            yield f'Drafting purchase agreement'

        @transition('REVIEWING')
        def review_agreement(state, cur_state):
            yield f'Reviewing purchase agreement'

        @transition('SIGNED')
        def sign_agreement(state, cur_state):
            yield f'Purchase agreement signed by all parties'

        @transition('COMPLETED')
        def complete_agreement(state, cur_state):
            yield f'Purchase agreement execution completed'

    # ==================================================================================
    # STAGE 04: OFFICIAL LOAN APPLICATION SUBMISSION STEPS
    # ==================================================================================

    class UploadSignedPurchaseAgreement(Step, name='Upload Signed Purchase Agreement', stage=Stage04_LoanSubmission):
        """Upload the signed purchase agreement to LOS"""
        __states__ = ('PENDING', 'UPLOADING', 'UPLOADED', 'VERIFIED', 'COMPLETED')

        @transition('UPLOADING')
        def start_upload(state, cur_state):
            yield f'Uploading signed purchase agreement'

        @transition('UPLOADED')
        def mark_uploaded(state, cur_state):
            yield f'Purchase agreement uploaded'

        @transition('VERIFIED')
        def verify_document(state, cur_state):
            yield f'Purchase agreement verified'

        @transition('COMPLETED')
        def complete_upload(state, cur_state):
            yield f'Purchase agreement upload completed'

    class CollectApplicationDocuments(Step, name='Collect Application Documents', stage=Stage04_LoanSubmission):
        """Collect all required documents for official loan application"""
        __states__ = ('PENDING', 'COLLECTING', 'REVIEWING', 'COMPLETE', 'NEEDS_MORE')

        @transition('COLLECTING')
        def start_collection(state, cur_state):
            yield f'Starting application document collection'

        @transition('REVIEWING')
        def review_documents(state, cur_state):
            yield f'Reviewing submitted application documents'

        @transition('COMPLETE')
        def mark_complete(state, cur_state):
            yield f'All application documents received'

        @transition('NEEDS_MORE')
        def request_more_documents(state, cur_state):
            yield f'Additional application documents needed'

    class GenerateLoanEstimate(Step, name='Generate Loan Estimate/Disclosures', stage=Stage04_LoanSubmission):
        """Generate loan estimate and required disclosures"""
        __states__ = ('PENDING', 'GENERATING', 'REVIEWING', 'SENT', 'RECEIVED', 'COMPLETED')

        @transition('GENERATING')
        def generate_estimate(state, cur_state):
            yield f'Generating loan estimate and disclosures'

        @transition('REVIEWING')
        def review_estimate(state, cur_state):
            yield f'Reviewing loan estimate'

        @transition('SENT')
        def send_estimate(state, cur_state):
            yield f'Loan estimate sent to borrower'

        @transition('RECEIVED')
        def acknowledge_receipt(state, cur_state):
            yield f'Borrower acknowledged receipt of loan estimate'

        @transition('COMPLETED')
        def complete_estimate(state, cur_state):
            yield f'Loan estimate process completed'

    # ==================================================================================
    # STAGE 05: UNDERWRITING SUBMISSION STEPS
    # ==================================================================================

    class PullCreditAndSubmitDU(Step, name='Pull Credit and Submit to DU', stage=Stage05_Underwriting):
        """Pull credit and submit data through Desktop Underwriter"""
        __states__ = ('PENDING', 'PULLING_CREDIT', 'SUBMITTING_DU', 'DU_COMPLETE', 'COMPLETED')

        @transition('PULLING_CREDIT')
        def pull_credit(state, cur_state):
            yield f'Pulling credit report for underwriting'

        @transition('SUBMITTING_DU')
        def submit_du(state, cur_state):
            yield f'Submitting to Desktop Underwriter'

        @transition('DU_COMPLETE')
        def complete_du(state, cur_state):
            yield f'Desktop Underwriter submission complete'

        @transition('COMPLETED')
        def complete_process(state, cur_state):
            yield f'Credit pull and DU submission completed'

    class OrderAppraisalAndTitle(Step, name='Order Appraisal & Title Work', stage=Stage05_Underwriting):
        """Order property appraisal and title work"""
        __states__ = ('PENDING', 'ORDERING', 'ORDERED', 'IN_PROGRESS', 'COMPLETED', 'ISSUES_FOUND')

        @transition('ORDERING')
        def start_ordering(state, cur_state):
            yield f'Ordering appraisal and title work'

        @transition('ORDERED')
        def mark_ordered(state, cur_state):
            yield f'Appraisal and title ordered'

        @transition('IN_PROGRESS')
        def mark_in_progress(state, cur_state):
            yield f'Appraisal and title work in progress'

        @transition('COMPLETED')
        def complete_work(state, cur_state):
            yield f'Appraisal and title work completed'

        @transition('ISSUES_FOUND')
        def flag_issues(state, cur_state):
            yield f'Issues found in appraisal or title'

    class ProcessingAndVerifications(Step, name='Processing & Verifications', stage=Stage05_Underwriting):
        """Complete processing and verify all documentation"""
        __states__ = ('PENDING', 'PROCESSING', 'VERIFYING', 'VERIFIED', 'ISSUES_FOUND', 'COMPLETED')

        @transition('PROCESSING')
        def start_processing(state, cur_state):
            yield f'Starting loan processing'

        @transition('VERIFYING')
        def verify_documents(state, cur_state):
            yield f'Verifying all loan documents'

        @transition('VERIFIED')
        def mark_verified(state, cur_state):
            yield f'All documents verified'

        @transition('ISSUES_FOUND')
        def flag_issues(state, cur_state):
            yield f'Issues found during verification'

        @transition('COMPLETED')
        def complete_processing(state, cur_state):
            yield f'Processing and verifications completed'

    class SubmitToUnderwriting(Step, name='Submit to Underwriting', stage=Stage05_Underwriting):
        """Submit complete loan package to underwriting"""
        __states__ = ('PENDING', 'PREPARING', 'SUBMITTED', 'IN_REVIEW', 'COMPLETED')

        @transition('PREPARING')
        def prepare_submission(state, cur_state):
            yield f'Preparing underwriting submission package'

        @transition('SUBMITTED')
        def submit_package(state, cur_state):
            yield f'Loan package submitted to underwriting'

        @transition('IN_REVIEW')
        def under_review(state, cur_state):
            yield f'Loan under underwriting review'

        @transition('COMPLETED')
        def complete_submission(state, cur_state):
            yield f'Underwriting submission completed'

    class ConditionalApproval(Step, name='Conditional Approval', stage=Stage05_Underwriting):
        """Receive conditional approval from underwriter"""
        __states__ = ('PENDING', 'REVIEWING', 'APPROVED_WITH_CONDITIONS', 'SUSPENDED', 'DENIED', 'COMPLETED')

        @transition('REVIEWING')
        def under_review(state, cur_state):
            yield f'Underwriter reviewing loan'

        @transition('APPROVED_WITH_CONDITIONS')
        def approve_with_conditions(state, cur_state):
            yield f'Loan approved with conditions'

        @transition('SUSPENDED')
        def suspend_loan(state, cur_state):
            yield f'Loan suspended pending additional information'

        @transition('DENIED')
        def deny_loan(state, cur_state):
            yield f'Loan denied by underwriter'

        @transition('COMPLETED')
        def complete_approval(state, cur_state):
            yield f'Conditional approval process completed'

    class SatisfyConditions(Step, name='Satisfy Underwriting Conditions', stage=Stage05_Underwriting):
        """Satisfy all underwriting conditions"""
        __states__ = ('PENDING', 'COLLECTING', 'SUBMITTING', 'UNDER_REVIEW', 'SATISFIED', 'ADDITIONAL_CONDITIONS', 'COMPLETED')

        @transition('COLLECTING')
        def collect_items(state, cur_state):
            yield f'Collecting items to satisfy conditions'

        @transition('SUBMITTING')
        def submit_items(state, cur_state):
            yield f'Submitting condition items to underwriter'

        @transition('UNDER_REVIEW')
        def under_review(state, cur_state):
            yield f'Underwriter reviewing submitted conditions'

        @transition('SATISFIED')
        def mark_satisfied(state, cur_state):
            yield f'All conditions satisfied'

        @transition('ADDITIONAL_CONDITIONS')
        def add_conditions(state, cur_state):
            yield f'Additional conditions issued'

        @transition('COMPLETED')
        def complete_conditions(state, cur_state):
            yield f'Condition satisfaction process completed'

    class ClearToClose(Step, name='Clear to Close (CTC)', stage=Stage05_Underwriting):
        """Receive final clear to close approval"""
        __states__ = ('PENDING', 'FINAL_REVIEW', 'CLEARED', 'COMPLETED')

        @transition('FINAL_REVIEW')
        def final_review(state, cur_state):
            yield f'Underwriter performing final review'

        @transition('CLEARED')
        def clear_loan(state, cur_state):
            yield f'Loan cleared to close'

        @transition('COMPLETED')
        def complete_ctc(state, cur_state):
            yield f'Clear to close process completed'

    # ==================================================================================
    # STAGE 06: CLOSING STEPS
    # ==================================================================================

    class PrepareClosingDisclosure(Step, name='Prepare Closing Disclosure (CD)', stage=Stage06_Closing):
        """Prepare and deliver closing disclosure to borrower"""
        __states__ = ('PENDING', 'PREPARING', 'REVIEWING', 'SENT', 'ACKNOWLEDGED', 'COMPLETED')

        @transition('PREPARING')
        def prepare_cd(state, cur_state):
            yield f'Preparing closing disclosure'

        @transition('REVIEWING')
        def review_cd(state, cur_state):
            yield f'Reviewing closing disclosure'

        @transition('SENT')
        def send_cd(state, cur_state):
            yield f'Closing disclosure sent to borrower'

        @transition('ACKNOWLEDGED')
        def acknowledge_cd(state, cur_state):
            yield f'Borrower acknowledged closing disclosure'

        @transition('COMPLETED')
        def complete_cd(state, cur_state):
            yield f'Closing disclosure process completed'

    class ArrangeFunding(Step, name='Arrange Funding', stage=Stage06_Closing):
        """Arrange loan funding with investor/warehouse"""
        __states__ = ('PENDING', 'REQUESTING', 'APPROVED', 'WIRED', 'COMPLETED')

        @transition('REQUESTING')
        def request_funding(state, cur_state):
            yield f'Requesting loan funding'

        @transition('APPROVED')
        def approve_funding(state, cur_state):
            yield f'Funding approved'

        @transition('WIRED')
        def wire_funds(state, cur_state):
            yield f'Funds wired to closing agent'

        @transition('COMPLETED')
        def complete_funding(state, cur_state):
            yield f'Funding arrangement completed'

    class ClosingAndSigning(Step, name='Closing & Signing', stage=Stage06_Closing):
        """Final closing meeting and document signing"""
        __states__ = ('PENDING', 'SCHEDULED', 'IN_PROGRESS', 'SIGNED', 'COMPLETED')

        @transition('SCHEDULED')
        def schedule_closing(state, cur_state):
            yield f'Closing appointment scheduled'

        @transition('IN_PROGRESS')
        def start_closing(state, cur_state):
            yield f'Closing meeting in progress'

        @transition('SIGNED')
        def sign_documents(state, cur_state):
            yield f'All closing documents signed'

        @transition('COMPLETED')
        def complete_closing(state, cur_state):
            yield f'Closing and signing completed - Loan funded!'

    # ==================================================================================
    # WORKFLOW EVENT HANDLERS
    # ==================================================================================

    def on_start(wf_state):
        """
        Initialize the workflow when started.
        Creates the first step in the pre-qualification stage.
        """
        logger.info(f"Starting Loan Application Process for workflow {wf_state._id}")
        
        # Start with the first step in Stage 01
        step1 = wf_state.add_step('CollectBasicInformation')
        step1.transit('PENDING')
        step2 = wf_state.add_step('TransferToLOS')
        step2.transit('PENDING')
        
        yield f"Loan Application Process started - initial step created"

    @connect('borrower-info-submitted')
    def handle_borrower_info_submitted(wf_state, event):
        """Handle borrower basic information submission"""
        wf_state.memorize(borrower_info_date=event.timestamp if hasattr(event, 'timestamp') else None)
        yield f"Borrower information submitted and recorded"

    @connect('soft-pull-completed')
    def handle_soft_pull_completed(wf_state, event):
        """Handle soft credit pull completion"""
        wf_state.memorize(
            soft_pull_date=event.timestamp if hasattr(event, 'timestamp') else None,
            credit_score=event.credit_score if hasattr(event, 'credit_score') else None
        )
        yield f"Soft credit pull completed - score recorded"

    @connect('pre-approval-issued')
    def handle_pre_approval_issued(wf_state, event):
        """Handle pre-approval letter issuance"""
        wf_state.memorize(
            pre_approval_date=event.timestamp if hasattr(event, 'timestamp') else None,
            pre_approval_amount=event.amount if hasattr(event, 'amount') else None
        )
        wf_state.output(file='pre-approval-letter.pdf')
        yield f"Pre-approval letter issued"

    @connect('purchase-agreement-signed')
    def handle_purchase_agreement_signed(wf_state, event):
        """Handle purchase agreement signing"""
        wf_state.memorize(
            purchase_agreement_date=event.timestamp if hasattr(event, 'timestamp') else None,
            property_address=event.property_address if hasattr(event, 'property_address') else None,
            purchase_price=event.purchase_price if hasattr(event, 'purchase_price') else None
        )
        wf_state.output(file='purchase-agreement.pdf')
        yield f"Purchase agreement signed and recorded"

    @connect('clear-to-close')
    def handle_clear_to_close(wf_state, event):
        """Handle clear to close notification"""
        wf_state.memorize(
            ctc_date=event.timestamp if hasattr(event, 'timestamp') else None
        )
        yield f"Clear to close received - ready for closing"

    @connect('loan-funded')
    def handle_loan_funded(wf_state, event):
        """Handle loan funding completion"""
        wf_state.memorize(
            funding_date=event.timestamp if hasattr(event, 'timestamp') else None,
            final_loan_amount=event.loan_amount if hasattr(event, 'loan_amount') else None
        )
        wf_state.output(message='Loan successfully funded!')
        wf_state.output(file='final-closing-documents.pdf')
        yield f"Loan funded successfully - process complete"

    def on_finished(wf_state):
        """Handle workflow completion"""
        yield f"Loan Application Process completed successfully for workflow {wf_state._id}"

    def on_cancelled(wf_state):
        """Handle workflow cancellation"""
        yield f"Loan Application Process cancelled for workflow {wf_state._id}"

