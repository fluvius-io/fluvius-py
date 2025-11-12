#!/usr/bin/env python
"""
Test script to demonstrate the gen_wfdefs() function.

This script shows how to extract workflow definition metadata from registered workflows.
"""

import sys
sys.path.insert(0, 'src')

from fluvius.navis.engine.manager import WorkflowManager
from fluvius.manager.workflow.import_definitions import gen_wfdefs
from loan_application import process  # Import to register the workflow

# Generate workflow definitions
print("Generating workflow definitions...\n")
wfdefs = gen_wfdefs(WorkflowManager)

print(f'Found {len(wfdefs)} workflow definition(s)')
print('=' * 80)

for wfdef in wfdefs:
    print(f"\nWorkflow Definition:")
    print(f"  Key: {wfdef['wfdef_key']}")
    print(f"  Revision: {wfdef['wfdef_rev']}")
    print(f"  Title: {wfdef['title']}")
    print(f"  Namespace: {wfdef['namespace']}")
    
    if wfdef.get('desc'):
        print(f"  Description: {wfdef['desc'][:100]}...")
    
    stages = wfdef.get('stages', []) or []
    steps = wfdef.get('steps', []) or []
    roles = wfdef.get('roles', []) or []
    
    print(f"\n  Statistics:")
    print(f"    - Stages: {len(stages)}")
    print(f"    - Steps: {len(steps)}")
    print(f"    - Roles: {len(roles)}")
    
    if stages:
        print(f"\n  Stages:")
        for stage in stages:
            print(f"    {stage['order']}. {stage['name']} ({stage['key']})")
    
    if roles:
        print(f"\n  Roles:")
        for role in roles:
            print(f"    - {role['title']} ({role['key']})")
    
    if steps:
        print(f"\n  Sample Steps (first 5):")
        for step in steps[:5]:
            print(f"    - {step['title']}")
            print(f"      Key: {step['key']}, Stage: {step.get('stage', 'N/A')}, Multiple: {step.get('multiple', False)}")

print('\n' + '=' * 80)
print("\nThis data structure is compatible with the WorkflowDefinition schema")
print("and can be stored in the workflow_definition table.")

