# Mutation Reference Guide

This document provides a comprehensive reference for all `MutationEnvelop` types in the Riparius workflow system and how they are persisted to the database.

## Overview

The mutation system in Riparius uses the Command pattern to capture changes to workflow state. Each mutation is wrapped in a `MutationEnvelop` that provides metadata about the operation.

## MutationEnvelop Structure

```python
class MutationEnvelop(WorkflowDataModel):
    name: str                           # Mutation type name (kebab-case)
    workflow_id: UUID_TYPE             # Target workflow ID
    step_id: Optional[UUID_TYPE]       # Target step ID (if applicable)
    action: str                        # Action name for logging/tracking
    mutation: WorkflowMutation         # The actual mutation data
```

## Available Mutation Types

### 1. CreateWorkflow

**Purpose**: Creates a new workflow in the system.

**Database Mapping**: → `WorkflowSchema` table

**Structure**:
```python
class CreateWorkflow(WorkflowMutation):
    workflow: WorkflowData
```

**Sample Usage**:
```python
MutationEnvelop(
    name='create-workflow',
    workflow_id=UUID('669d761a-3e32-4032-870f-4b4e2cd7e03e'),
    step_id=None,
    action='create-workflow',
    mutation=CreateWorkflow(
        workflow=WorkflowData(
            id=UUID('669d761a-3e32-4032-870f-4b4e2cd7e03e'),
            title='Sample Process',
            revision=1,
            route_id=UUID('3b7029cd-91f0-5fb7-bfd3-ae3215e55a69'),
            status=WorkflowStatus.NEW,
            progress=0.0
        )
    )
)
```

### 2. UpdateWorkflow

**Purpose**: Updates properties of an existing workflow.

**Database Mapping**: → `WorkflowSchema` table (UPDATE)

**Structure**:
```python
class UpdateWorkflow(WorkflowMutation):
    status: WorkflowStatus = Field(default=WorkflowStatus.NEW)
    progress: float = Field(default=0.0)
    etag: str = Field(default=None)
    ts_start: Optional[datetime] = None
    ts_expire: Optional[datetime] = None
    ts_finish: Optional[datetime] = None
    ts_transit: Optional[datetime] = None
```

**Sample Usage**:
```python
MutationEnvelop(
    name='update-workflow',
    workflow_id=UUID('669d761a-3e32-4032-870f-4b4e2cd7e03e'),
    step_id=None,
    action='start',
    mutation=UpdateWorkflow(
        status=WorkflowStatus.ACTIVE,
        progress=0.0,
        ts_start=datetime.now(timezone.utc)
    )
)
```

### 3. AddStep

**Purpose**: Adds a new step to a workflow.

**Database Mapping**: → `WorkflowStep` table

**Structure**:
```python
class AddStep(WorkflowMutation):
    step: WorkflowStep
```

**Sample Usage**:
```python
MutationEnvelop(
    name='add-step',
    workflow_id=UUID('669d761a-3e32-4032-870f-4b4e2cd7e03e'),
    step_id=UUID('1f62adbe-d99f-566d-b14c-b2647c52f845'),
    action='add-step',
    mutation=AddStep(
        step=WorkflowStep(
            id=UUID('1f62adbe-d99f-566d-b14c-b2647c52f845'),
            selector=UUID('652dfe93-337e-5ea3-bb54-c173547a00c2'),
            workflow_id=UUID('669d761a-3e32-4032-870f-4b4e2cd7e03e'),
            title='Step 03',
            stm_state='_CREATED',
            status=StepStatus.ACTIVE,
            label='NEW'
        )
    )
)
```

### 4. UpdateStep

**Purpose**: Updates properties of an existing step.

**Database Mapping**: → `WorkflowStep` table (UPDATE)

**Structure**:
```python
class UpdateStep(WorkflowMutation):
    title: Optional[str] = None
    stm_state: Optional[str] = None
    message: Optional[str] = None
    status: Optional[StepStatus] = None
    label: Optional[str] = None
    ts_due: Optional[datetime] = None
    ts_start: Optional[datetime] = None
    ts_finish: Optional[datetime] = None
    ts_transit: Optional[datetime] = None
```

**Sample Usage**:
```python
MutationEnvelop(
    name='update-step',
    workflow_id=UUID('669d761a-3e32-4032-870f-4b4e2cd7e03e'),
    step_id=UUID('1f62adbe-d99f-566d-b14c-b2647c52f845'),
    action='transit',
    mutation=UpdateStep(
        stm_state='MOON',
        status=StepStatus.ACTIVE,
        ts_transit=datetime.now(timezone.utc)
    )
)
```

### 5. SetMemory

**Purpose**: Stores key-value data in workflow or step memory.

**Database Mapping**: → `WorkflowMemory` table

**Structure**:
```python
class SetMemory(WorkflowMutation):
    data: dict
```

**Sample Usage**:
```python
MutationEnvelop(
    name='set-memory',
    workflow_id=UUID('669d761a-3e32-4032-870f-4b4e2cd7e03e'),
    step_id=None,  # Workflow-level memory
    action='memorize',
    mutation=SetMemory(
        data={'test_step_key': 'value'}
    )
)
```

### 6. AddTrigger

**Purpose**: Records trigger events and their data.

**Database Mapping**: → `WorkflowTrigger` table

**Structure**:
```python
class AddTrigger(WorkflowMutation):
    name: str
    data: dict
```

**Sample Usage**:
```python
MutationEnvelop(
    name='add-trigger',
    workflow_id=UUID('669d761a-3e32-4032-870f-4b4e2cd7e03e'),
    step_id=None,
    action='trigger',
    mutation=AddTrigger(
        name='test_event_step',
        data={'workflow_id': UUID('3b7029cd-91f0-5fb7-bfd3-ae3215e55a69')}
    )
)
```

### 7. AddParticipant

**Purpose**: Adds a user to a workflow with a specific role.

**Database Mapping**: → `WorkflowParticipant` table

**Structure**:
```python
class AddParticipant(WorkflowMutation):
    user_id: UUID_TYPE
    role: str
```

### 8. DelParticipant

**Purpose**: Removes a user from a workflow.

**Database Mapping**: → `WorkflowParticipant` table (DELETE)

**Structure**:
```python
class DelParticipant(WorkflowMutation):
    user_id: Optional[UUID_TYPE] = None
```

### 9. AddStage

**Purpose**: Adds a stage definition to a workflow.

**Database Mapping**: → `WorkflowStage` table

**Structure**:
```python
class AddStage(WorkflowMutation):
    data: WorkflowStage
```

### 10. AddRole

**Purpose**: Defines a new role type for workflows.

**Database Mapping**: Not directly persisted (used for role definitions)

**Structure**:
```python
class AddRole(WorkflowMutation):
    name: str
```

## Database Schema Mapping

| Mutation Type | Target Table | Operation |
|---------------|-------------|-----------|
| `CreateWorkflow` | `WorkflowSchema` | INSERT |
| `UpdateWorkflow` | `WorkflowSchema` | UPDATE |
| `AddStep` | `WorkflowStep` | INSERT |
| `UpdateStep` | `WorkflowStep` | UPDATE |
| `SetMemory` | `WorkflowMemory` | UPSERT |
| `AddTrigger` | `WorkflowTrigger` | INSERT |
| `AddParticipant` | `WorkflowParticipant` | INSERT |
| `DelParticipant` | `WorkflowParticipant` | DELETE |
| `AddStage` | `WorkflowStage` | INSERT |
| `AddRole` | *(not persisted)* | - |

## Usage in WorkflowManager

The `WorkflowManager.persist_mutations()` method processes lists of mutations and persists them to the database:

```python
# Example usage
mutations = workflow_engine.consume_mutations()
summary = await workflow_manager.persist_mutations(mutations)
print(f"Processed {summary['total_processed']} mutations")
```

## Mutation Registration

All mutation classes are automatically registered in the `REGISTRY` dictionary by their kebab-case names:

```python
# In mutation.py
REGISTRY = {
    'create-workflow': CreateWorkflow,
    'update-workflow': UpdateWorkflow,
    'add-step': AddStep,
    'update-step': UpdateStep,
    'set-memory': SetMemory,
    'add-trigger': AddTrigger,
    'add-participant': AddParticipant,
    'del-participant': DelParticipant,
    'add-stage': AddStage,
    'add-role': AddRole
}
```

## Error Handling

The persistence system includes comprehensive error handling:

- Transaction rollback on any mutation failure
- Detailed logging of failed mutations
- Summary statistics of successful operations
- Graceful handling of unknown mutation types

## Performance Considerations

- All mutations in a batch are processed within a single database transaction
- Memory mutations use UPSERT to handle key updates efficiently
- Bulk operations are preferred over individual inserts where possible 