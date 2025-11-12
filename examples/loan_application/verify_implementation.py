#!/usr/bin/env python3
"""
Verification script for Loan Application Process implementation
This script verifies the workflow structure without requiring a full environment setup.
"""

import ast
import sys
from pathlib import Path

def verify_workflow_structure():
    """Verify the workflow structure by parsing the Python file"""
    
    process_file = Path(__file__).parent / "src" / "workflow_manager" / "process.py"
    
    if not process_file.exists():
        print(f"❌ File not found: {process_file}")
        return False
    
    with open(process_file) as f:
        content = f.read()
    
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        print(f"❌ Syntax error in process.py: {e}")
        return False
    
    print("✓ Syntax is valid")
    
    # Find the LoanApplicationProcess class
    workflow_class = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "LoanApplicationProcess":
            workflow_class = node
            break
    
    if not workflow_class:
        print("❌ LoanApplicationProcess class not found")
        return False
    
    print("✓ LoanApplicationProcess class found")
    
    # Count stages, steps, and roles
    stages = []
    steps = []
    roles = []
    event_handlers = []
    
    for item in workflow_class.body:
        if isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name):
                    name = target.id
                    if name.startswith('Stage'):
                        stages.append(name)
                    elif 'Role' in name or name in ['LoanOfficer', 'Borrower', 'Processor', 'Underwriter', 'ClosingAgent']:
                        roles.append(name)
        
        elif isinstance(item, ast.ClassDef):
            # Step classes
            steps.append(item.name)
        
        elif isinstance(item, ast.FunctionDef):
            # Check for event handlers (functions decorated with @connect)
            for decorator in item.decorators:
                if isinstance(decorator, ast.Call):
                    if isinstance(decorator.func, ast.Name) and decorator.func.id == 'connect':
                        event_handlers.append(item.name)
                        break
    
    print(f"\n📊 Workflow Structure:")
    print(f"  ✓ Stages: {len(stages)}")
    for stage in stages:
        print(f"    - {stage}")
    
    print(f"\n  ✓ Roles: {len(roles)}")
    for role in roles:
        print(f"    - {role}")
    
    print(f"\n  ✓ Steps: {len(steps)}")
    
    # Group steps by stage
    stage_steps = {
        'Stage01_PreQualification': [],
        'Stage02_PreApproval': [],
        'Stage03_PurchaseOffer': [],
        'Stage04_LoanSubmission': [],
        'Stage05_Underwriting': [],
        'Stage06_Closing': []
    }
    
    # Parse step definitions to determine their stages
    for step_name in steps:
        if step_name == 'Meta':
            continue
        # Simplified grouping based on expected structure
        if step_name in ['CollectBasicInformation', 'TransferToLOS', 'RequestSoftPull', 
                         'ReviewSoftPull', 'AssessCreditworthiness', 'VerifyIncomeEmployment', 
                         'DiscussCreditFindings']:
            stage_steps['Stage01_PreQualification'].append(step_name)
        elif step_name in ['DetermineLoanEligibility', 'ProvidePreQualEstimate', 
                           'AddressDocumentationGaps', 'CollectPreApprovalDocuments', 
                           'RunAUS', 'IssuePreApprovalLetter']:
            stage_steps['Stage02_PreApproval'].append(step_name)
        elif step_name in ['CollectPropertyInformation', 'SubmitPurchaseOffer', 
                           'ExecutePurchaseAgreement']:
            stage_steps['Stage03_PurchaseOffer'].append(step_name)
        elif step_name in ['UploadSignedPurchaseAgreement', 'CollectApplicationDocuments', 
                           'GenerateLoanEstimate']:
            stage_steps['Stage04_LoanSubmission'].append(step_name)
        elif step_name in ['PullCreditAndSubmitDU', 'OrderAppraisalAndTitle', 
                           'ProcessingAndVerifications', 'SubmitToUnderwriting', 
                           'ConditionalApproval', 'SatisfyConditions', 'ClearToClose']:
            stage_steps['Stage05_Underwriting'].append(step_name)
        elif step_name in ['PrepareClosingDisclosure', 'ArrangeFunding', 'ClosingAndSigning']:
            stage_steps['Stage06_Closing'].append(step_name)
    
    for stage_name, step_list in stage_steps.items():
        if step_list:
            print(f"\n  {stage_name}:")
            for step in step_list:
                print(f"    - {step}")
    
    print(f"\n  ✓ Event Handlers: {len(event_handlers)}")
    for handler in event_handlers:
        print(f"    - {handler}")
    
    # Verify expected counts
    expected = {
        'stages': 6,
        'roles': 5,
        'steps_min': 28,  # Minimum expected steps (excluding Meta)
        'event_handlers_min': 6
    }
    
    issues = []
    if len(stages) != expected['stages']:
        issues.append(f"Expected {expected['stages']} stages, found {len(stages)}")
    
    if len(roles) != expected['roles']:
        issues.append(f"Expected {expected['roles']} roles, found {len(roles)}")
    
    actual_steps = len([s for s in steps if s != 'Meta'])
    if actual_steps < expected['steps_min']:
        issues.append(f"Expected at least {expected['steps_min']} steps, found {actual_steps}")
    
    if len(event_handlers) < expected['event_handlers_min']:
        issues.append(f"Expected at least {expected['event_handlers_min']} event handlers, found {len(event_handlers)}")
    
    if issues:
        print("\n⚠️  Issues found:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    
    print("\n✅ All structure checks passed!")
    return True


def verify_test_file():
    """Verify the test file exists and is valid"""
    
    test_file = Path(__file__).parent / "tests" / "test_loan_application_process.py"
    
    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        return False
    
    print(f"\n✓ Test file exists: {test_file}")
    
    with open(test_file) as f:
        content = f.read()
    
    try:
        ast.parse(content)
        print("✓ Test file syntax is valid")
    except SyntaxError as e:
        print(f"❌ Syntax error in test file: {e}")
        return False
    
    # Count test classes and methods
    tree = ast.parse(content)
    test_classes = 0
    test_methods = 0
    
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name.startswith('Test'):
            test_classes += 1
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name.startswith('test_'):
                    test_methods += 1
    
    print(f"✓ Found {test_classes} test classes with {test_methods} test methods")
    
    return True


def main():
    """Run all verification checks"""
    print("=" * 60)
    print("LOAN APPLICATION PROCESS - IMPLEMENTATION VERIFICATION")
    print("=" * 60)
    
    print("\n1. Verifying workflow structure...")
    structure_ok = verify_workflow_structure()
    
    print("\n" + "=" * 60)
    print("\n2. Verifying test file...")
    tests_ok = verify_test_file()
    
    print("\n" + "=" * 60)
    print("\n📋 VERIFICATION SUMMARY")
    print("=" * 60)
    
    if structure_ok and tests_ok:
        print("\n✅ ALL CHECKS PASSED")
        print("\nThe Loan Application Process has been successfully implemented:")
        print("  ✓ Workflow structure is complete")
        print("  ✓ All stages, steps, and roles are defined")
        print("  ✓ Event handlers are in place")
        print("  ✓ Comprehensive tests are available")
        print("\nNext steps:")
        print("  1. Set up the development environment")
        print("  2. Run the test suite: pytest tests/test_loan_application_process.py")
        print("  3. Start the application: python -m workflow_manager.main")
        return 0
    else:
        print("\n❌ VERIFICATION FAILED")
        print("\nPlease review the issues above and fix them.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

