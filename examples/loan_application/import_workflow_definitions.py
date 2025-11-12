#!/usr/bin/env python
"""
Import workflow definitions into the workflow_definition table.

This script demonstrates how to use the gen_wfdefs() function and import
workflow definitions into the workflow_definition table.

Usage:
    python import_workflow_definitions.py [--force]
    
Options:
    --force    Update existing workflow definitions (default: skip existing)
"""

import sys
import asyncio
sys.path.insert(0, 'src')

from fluvius.navis.engine.manager import WorkflowManager
from fluvius.navis.model import WorkflowDataManager
from fluvius.manager.workflow.import_definitions import gen_wfdefs

# Import your workflows to register them
from loan_application import process


async def main():
    """Import workflow definitions into the database."""
    
    # Check for --force flag
    force = '--force' in sys.argv
    
    print("=" * 80)
    print("Workflow Definition Import")
    print("=" * 80)
    print(f"\nMode: {'Force update' if force else 'Insert new only'}")
    print(f"Registered workflows: {len(WorkflowManager.__registry__)}")
    
    for wfdef_key in WorkflowManager.__registry__.keys():
        print(f"  - {wfdef_key}")
    
    print("\nGenerating workflow definitions...")
    
    # Generate workflow definitions
    wfdefs = gen_wfdefs(WorkflowManager)
    
    print(f"Generated {len(wfdefs)} workflow definition(s)")
    print("\nImporting into database...\n")
    
    # Create data manager
    data_manager = WorkflowDataManager()
    
    # Import workflow definitions
    inserted = 0
    updated = 0
    skipped = 0
    errors = []
    
    try:
        for wfdef in wfdefs:
            try:
                # Check if definition already exists
                existing = await data_manager.find_one(
                    'workflow_definition',
                    where={
                        'wfdef_key': wfdef['wfdef_key'],
                        'wfdef_rev': wfdef['wfdef_rev']
                    }
                )
                
                if existing:
                    if force:
                        # Update existing definition
                        await data_manager.update_data(
                            'workflow_definition',
                            existing['_id'],
                            **wfdef
                        )
                        updated += 1
                        print(f"  ↻ Updated: {wfdef['wfdef_key']} (rev {wfdef['wfdef_rev']})")
                    else:
                        skipped += 1
                        print(f"  − Skipped: {wfdef['wfdef_key']} (rev {wfdef['wfdef_rev']})")
                else:
                    # Insert new definition
                    await data_manager.insert_one('workflow_definition', wfdef)
                    inserted += 1
                    print(f"  ✓ Inserted: {wfdef['wfdef_key']} (rev {wfdef['wfdef_rev']})")
                    
            except Exception as e:
                error_msg = f"Error importing {wfdef['wfdef_key']}: {str(e)}"
                errors.append(error_msg)
                print(f"  ✗ Error: {wfdef['wfdef_key']} - {str(e)}")
        
        result = {
            'total': len(wfdefs),
            'inserted': inserted,
            'updated': updated,
            'skipped': skipped,
            'errors': errors
        }
        
        # Display results
        print("=" * 80)
        print("Import Results")
        print("=" * 80)
        print(f"\nTotal workflows processed: {result['total']}")
        print(f"  ✓ Inserted: {result['inserted']}")
        print(f"  ↻ Updated:  {result['updated']}")
        print(f"  - Skipped:  {result['skipped']}")
        print(f"  ✗ Errors:   {len(result['errors'])}")
        
        if result['errors']:
            print("\nErrors:")
            for error in result['errors']:
                print(f"  ! {error}")
        
        print("\n" + "=" * 80)
        
        if result['inserted'] > 0 or result['updated'] > 0:
            print("✓ Workflow definitions successfully imported!")
        elif result['skipped'] > 0:
            print("→ All workflow definitions already exist. Use --force to update.")
        else:
            print("→ No workflow definitions imported.")
            
        print("=" * 80)
        
        # Return exit code based on results
        return 0 if len(result['errors']) == 0 else 1
        
    except Exception as e:
        print(f"\n✗ Error during import: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

