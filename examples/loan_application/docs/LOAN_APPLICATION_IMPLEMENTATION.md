# Loan Application Process Implementation

## Overview

This document describes the complete implementation of the Loan Application Process workflow using the `fluvius.navis` framework. The implementation follows industry-standard mortgage lending practices and covers the entire loan lifecycle from pre-qualification through closing.

## Architecture

### Workflow Definition

The loan application process is implemented as a `Workflow` class that inherits from `fluvius.navis.Workflow`. It consists of:

- **6 Stages**: Major phases of the loan application process
- **29 Steps**: Individual tasks and activities within each stage
- **5 Roles**: Participants involved in the process
- **6 Event Handlers**: Workflow events for key milestones

### File Structure

```
examples/loan_application/
├── src/
│   └── loan_application/
│       ├── __init__.py          # App configuration and workflow registration
│       ├── main.py              # FastAPI application entry point
│       └── process.py           # Loan Application Process workflow definition
├── tests/
│   ├── conftest.py              # Test fixtures and configuration
│   └── test_loan_application_process.py  # Comprehensive workflow tests
└── docs/
    ├── LOAN-APPLICATION-PROCESS.md       # Process specification
    └── LOAN_APPLICATION_IMPLEMENTATION.md # This file
```

## Workflow Structure

### Metadata

```python
class Meta:
    title = "Loan Application Process"
    revision = 1
    namespace = "lending"
```

### Roles

The workflow defines 5 participant roles:

1. **LoanOfficer**: Manages the loan application and communicates with borrower
2. **Borrower**: The individual applying for the loan
3. **Processor**: Processes documentation and coordinates underwriting
4. **Underwriter**: Reviews and approves the loan
5. **ClosingAgent**: Handles the final closing and funding

### Stages

#### Stage 01: PRE-QUALIFICATION
Initial borrower assessment with soft credit pull

**Steps:**
1. `CollectBasicInformation` - Borrower provides basic information
2. `TransferToLOS` - LO transfers data to Loan Origination System
3. `RequestSoftPull` - Request soft credit pull from bureau
4. `ReviewSoftPull` - Review the soft credit report
5. `AssessCreditworthiness` - Assess borrower creditworthiness
6. `VerifyIncomeEmployment` - Verify income and employment
7. `DiscussCreditFindings` - Discuss findings with borrower

#### Stage 02: PRE-APPROVAL
Formal pre-approval with hard credit pull and AUS

**Steps:**
1. `DetermineLoanEligibility` - Determine if borrower is eligible
2. `ProvidePreQualEstimate` - Provide pre-qualification estimate
3. `AddressDocumentationGaps` - Address any documentation gaps
4. `CollectPreApprovalDocuments` - Collect required documents
5. `RunAUS` - Run Automated Underwriting System (DU/LP)
6. `IssuePreApprovalLetter` - Issue the pre-approval letter

#### Stage 03: PURCHASE OFFER
Property identification and purchase agreement

**Steps:**
1. `CollectPropertyInformation` - Collect property details
2. `SubmitPurchaseOffer` - Submit offer on the property
3. `ExecutePurchaseAgreement` - Execute purchase agreement

#### Stage 04: OFFICIAL LOAN APPLICATION SUBMISSION
Official application submission with documentation

**Steps:**
1. `UploadSignedPurchaseAgreement` - Upload signed purchase agreement
2. `CollectApplicationDocuments` - Collect all application documents
3. `GenerateLoanEstimate` - Generate loan estimate and disclosures

#### Stage 05: UNDERWRITING SUBMISSION
Underwriting review and conditional approval

**Steps:**
1. `PullCreditAndSubmitDU` - Pull credit and submit to DU
2. `OrderAppraisalAndTitle` - Order appraisal and title work
3. `ProcessingAndVerifications` - Complete processing and verifications
4. `SubmitToUnderwriting` - Submit complete package to underwriting
5. `ConditionalApproval` - Receive conditional approval
6. `SatisfyConditions` - Satisfy underwriting conditions
7. `ClearToClose` - Receive clear to close approval

#### Stage 06: CLOSING
Final closing and funding

**Steps:**
1. `PrepareClosingDisclosure` - Prepare and send closing disclosure
2. `ArrangeFunding` - Arrange loan funding
3. `ClosingAndSigning` - Final closing meeting and signing

## Step State Management

Each step has a defined set of states that track its progress. For example:

### CollectBasicInformation States
- `_CREATED` (BEGIN_STATE) - Step just created
- `PENDING` - Waiting to start
- `COLLECTING` - Actively collecting information
- `COMPLETED` - Collection complete
- `_FINISHED` (FINISH_STATE) - Step finished

### RunAUS States
- `_CREATED`
- `PENDING`
- `RUNNING` - AUS system running
- `APPROVE_ELIGIBLE` - AUS approved
- `REFER` - Referred to manual underwriting
- `COMPLETED`
- `_FINISHED`

Steps transition between states using the `@transition` decorator:

```python
@transition('COLLECTING')
def start_collection(state, cur_state):
    yield f'Starting basic information collection for borrower'
```

## Event Handlers

The workflow responds to 6 key events:

### 1. borrower-info-submitted
Triggered when borrower submits basic information
- Records borrower info submission date

### 2. soft-pull-completed
Triggered when soft credit pull is complete
- Records credit score and pull date

### 3. pre-approval-issued
Triggered when pre-approval letter is issued
- Records pre-approval amount and date
- Outputs pre-approval letter PDF

### 4. purchase-agreement-signed
Triggered when purchase agreement is signed
- Records property address and purchase price
- Outputs purchase agreement PDF

### 5. clear-to-close
Triggered when underwriter issues clear to close
- Records CTC date

### 6. loan-funded
Triggered when loan funding is complete
- Records final loan amount and funding date
- Outputs final closing documents
- Marks workflow as complete

## Usage Examples

### Creating a Loan Application Workflow

```python
from fluvius.navis import WorkflowManager

manager = WorkflowManager()
async with manager._datamgr.transaction():
    wf = manager.create_workflow(
        'loan-application-process',
        'loan-application',
        resource_id,
        {
            'borrower_name': 'John Doe',
            'loan_amount': 350000,
            'property_type': 'Single Family'
        }
    )
    
    with wf.transaction():
        wf.start()
    
    await manager.commit()
```

### Starting the Workflow via API

```bash
POST /api/v1/workflow/create-workflow
{
  "wfdef_key": "loan-application-process",
  "resource_name": "loan-application",
  "resource_id": "uuid-here",
  "title": "John Doe - 123 Main St",
  "params": {
    "borrower_name": "John Doe",
    "loan_amount": 350000,
    "property_type": "Single Family"
  }
}
```

### Adding Participants

```bash
POST /api/v1/workflow/add-participant
{
  "user_id": "loan-officer-uuid",
  "role": "LoanOfficer"
}
```

### Injecting Events

```bash
POST /api/v1/workflow/inject-event
{
  "event_name": "soft-pull-completed",
  "event_data": {
    "resource_name": "loan-application",
    "resource_id": "uuid-here",
    "timestamp": "2024-01-15T11:00:00Z",
    "credit_score": 720,
    "bureau": "Experian"
  }
}
```

## Testing

Comprehensive tests are provided in `tests/test_loan_application_process.py`:

### Test Categories

1. **Structure Tests** - Verify workflow structure (stages, steps, roles)
2. **Workflow Tests** - Test workflow creation and management
3. **Event Tests** - Test event handling and injection
4. **Transition Tests** - Test step state transitions
5. **Lifecycle Tests** - Test complete workflow scenarios
6. **Documentation Tests** - Verify proper documentation

### Running Tests

```bash
# Run all loan application tests
pytest tests/test_loan_application_process.py -v

# Run specific test class
pytest tests/test_loan_application_process.py::TestLoanApplicationProcessStructure -v

# Run with coverage
pytest tests/test_loan_application_process.py --cov=workflow_manager --cov-report=html
```

## Workflow Memory

The workflow uses memory to store key information throughout the process:

```python
# Memory fields set by event handlers
{
    'borrower_info_date': timestamp,
    'soft_pull_date': timestamp,
    'credit_score': int,
    'pre_approval_date': timestamp,
    'pre_approval_amount': float,
    'purchase_agreement_date': timestamp,
    'property_address': str,
    'purchase_price': float,
    'ctc_date': timestamp,
    'funding_date': timestamp,
    'final_loan_amount': float
}
```

## Workflow Outputs

The workflow generates outputs at key milestones:

1. **Pre-Approval Letter** (`pre-approval-letter.pdf`)
2. **Purchase Agreement** (`purchase-agreement.pdf`)
3. **Final Closing Documents** (`final-closing-documents.pdf`)
4. **Success Message** - When loan is funded

## Extension Points

The workflow can be extended in several ways:

### Adding Custom Steps

```python
class CustomStep(Step, name='Custom Step', stage=Stage01_PreQualification):
    """Custom step description"""
    __states__ = ('PENDING', 'PROCESSING', 'COMPLETED')
    
    @transition('PROCESSING')
    def start_processing(state, cur_state):
        yield f'Starting custom processing'
```

### Adding Custom Events

```python
@connect('custom-event')
def handle_custom_event(wf_state, event):
    """Handle custom event"""
    wf_state.memorize(custom_field=event.value)
    yield f"Custom event processed"
```

### Adding Custom Roles

```python
CustomRole = Role(title="Custom Role")
```

## Best Practices

1. **Always use transactions** when modifying workflow state
2. **Commit workflows** after making changes
3. **Use events** to communicate between systems
4. **Store important data** in workflow memory
5. **Document all custom steps** with clear docstrings
6. **Test thoroughly** before deploying to production

## Integration with External Systems

The workflow can integrate with external systems through events:

- **LOS (Loan Origination System)** - Via data transfer steps
- **Credit Bureaus** - Via soft/hard pull events
- **AUS Systems** - Via DU/LP integration steps
- **Appraisal Services** - Via order and completion events
- **Title Companies** - Via title work coordination
- **Funding Systems** - Via funding arrangement steps

## Troubleshooting

### Workflow Won't Start
- Ensure workflow is properly registered in `__init__.py`
- Check that all imports are correct
- Verify database connection is working

### Step Transitions Fail
- Check that target state is in step's `__states__`
- Verify transition is called within a transaction
- Review transition decorator configuration

### Events Not Processing
- Ensure event handler is decorated with `@connect`
- Verify event data includes required fields
- Check that workflow ID matches event target

## Performance Considerations

1. **Batch Operations** - Use transactions to batch multiple changes
2. **Event Processing** - Events are processed asynchronously
3. **Database Access** - Minimize queries within step transitions
4. **Memory Usage** - Don't store large objects in workflow memory

## Security Considerations

1. **Authentication** - All API endpoints require authentication
2. **Authorization** - Check user roles before allowing actions
3. **Data Privacy** - Sensitive borrower data should be encrypted
4. **Audit Trail** - All workflow actions are logged

## Future Enhancements

Potential enhancements for future versions:

1. **Automated Document Collection** - Integration with document upload services
2. **Real-time Status Updates** - WebSocket notifications for status changes
3. **Workflow Analytics** - Dashboard showing pipeline metrics
4. **Automated Reminders** - Notifications for pending actions
5. **Mobile Support** - Mobile app for borrower interaction
6. **AI Assistance** - Automated document review and data extraction

## Support

For questions or issues with the Loan Application Process workflow:

1. Review this documentation
2. Check the test files for usage examples
3. Consult the fluvius.navis framework documentation
4. Contact the development team

## References

- [LOAN-APPLICATION-PROCESS.md](./LOAN-APPLICATION-PROCESS.md) - Process specification
- Fluvius Navis Framework Documentation
- Sample Process Implementation: `src/fluvius_test/navis_app/process.py`
- Navis Tests: `tests/fluvius_navis/test_workflow.py`

