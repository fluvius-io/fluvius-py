# Fluv

ius Navis API Endpoints

## Endpoint Structure

The fluvius framework uses a specific URL structure for API endpoints:

```
/{domain}:{command}/{resource}/{identifier}
```

Where:
- **domain**: The domain namespace (e.g., `process`)
- **command**: The command key (e.g., `create-workflow`)
- **resource**: The resource type (e.g., `workflow`)
- **identifier**: The resource ID or `:new` for creating new resources

## Workflow Command Endpoints

### Create Workflow
```
POST /process:create-workflow/workflow/:new
```

**Body:**
```json
{
  "wfdef_key": "loan-application-process",
  "resource_name": "loan-application",
  "resource_id": "<uuid>",
  "title": "Workflow Title",
  "params": {}
}
```

### Start Workflow
```
POST /process:start-workflow/workflow/{workflow_id}
```

**Body:**
```json
{
  "start_params": {}
}
```

### Add Participant
```
POST /process:add-participant/workflow/{workflow_id}
```

**Body:**
```json
{
  "user_id": "<uuid>",
  "role": "LoanOfficer"
}
```

### Remove Participant
```
POST /process:remove-participant/workflow/{workflow_id}
```

**Body:**
```json
{
  "user_id": "<uuid>",
  "role": "LoanOfficer"
}
```

### Update Workflow
```
POST /process:update-workflow/workflow/{workflow_id}
```

**Body:**
```json
{
  "progress": 0.5,
  "status": "ACTIVE"
}
```

### Cancel Workflow
```
POST /process:cancel-workflow/workflow/{workflow_id}
```

**Body:**
```json
{
  "reason": "Cancellation reason"
}
```

### Abort Workflow
```
POST /process:abort-workflow/workflow/{workflow_id}
```

**Body:**
```json
{
  "reason": "Abort reason"
}
```

### Ignore Step
```
POST /process:ignore-step/workflow/{workflow_id}
```

**Body:**
```json
{
  "step_id": "<uuid>",
  "reason": "Optional reason"
}
```

### Cancel Step
```
POST /process:cancel-step/workflow/{workflow_id}
```

**Body:**
```json
{
  "step_id": "<uuid>",
  "reason": "Optional reason"
}
```

### Inject Event
```
POST /process:inject-event/workflow/{workflow_id}
```

**Body:**
```json
{
  "event_name": "soft-pull-completed",
  "event_data": {
    "resource_name": "loan-application",
    "resource_id": "<uuid>",
    "credit_score": 720,
    "timestamp": "2024-01-15T11:00:00Z"
  }
}
```

### Add Role
```
POST /process:add-role/workflow/{workflow_id}
```

**Body:**
```json
{
  "role_name": "CustomRole"
}
```

### Remove Role
```
POST /process:remove-role/workflow/{workflow_id}
```

**Body:**
```json
{
  "role_name": "CustomRole"
}
```

### Send Trigger
```
POST /process:send-trigger/workflow/{workflow_id}
```

**Body:**
```json
{
  "trigger_type": "reminder",
  "target_id": "<uuid>",
  "delay_seconds": 3600
}
```

## Query Endpoints

### Get Workflow
```
GET /process.workflow/{workflow_id}
```

### List Workflows
```
GET /process.workflow/
```

### Get Workflow Steps
```
GET /process.workflow-step/{scope}/{identifier}
```

### Get Workflow Stages
```
GET /process.workflow-stage/{scope}/{identifier}
```

### Get Workflow Participants
```
GET /process.workflow-participant/{scope}/{identifier}
```

## Response Format

All command endpoints return a response in this format:

```json
{
  "status": "success",
  "data": {
    // Response data
  }
}
```

Error responses:

```json
{
  "status": "error",
  "message": "Error description",
  "code": "ERROR_CODE"
}
```

## Testing Example

```python
import pytest
from httpx import AsyncClient, ASGITransport
from fluvius.data import UUID_GENR

async def test_create_and_start_workflow(client: AsyncClient):
    # Create workflow
    resource_id = UUID_GENR()
    create_response = await client.post(
        "/process:create-workflow/workflow/:new",
        json={
            "wfdef_key": "loan-application-process",
            "resource_name": "loan-application",
            "resource_id": str(resource_id),
            "title": "Test Loan",
            "params": {"borrower_name": "John Doe"}
        }
    )
    
    assert create_response.status_code == 200
    workflow_data = create_response.json()
    workflow_id = workflow_data["id"]
    
    # Start workflow
    start_response = await client.post(
        f"/process:start-workflow/workflow/{workflow_id}",
        json={"start_params": {}}
    )
    
    assert start_response.status_code == 200
```

## Notes

- All command endpoints require authentication by default
- The `:new` identifier is used when creating new resources
- Use actual UUIDs for existing resources
- The domain namespace `process` is defined in `fluvius.navis._meta.defaults.DOMAIN_NAMESPACE`
- Command keys are defined in each command class's `Meta.key` attribute

