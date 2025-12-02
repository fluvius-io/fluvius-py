# Fluvius Error Codes Reference

This document provides a comprehensive reference of all error codes used in the Fluvius library.

## Error Code Format

Error codes follow the format: `X##.###` where:
- `X` = Single uppercase letter indicating the module
- `##` = Two-digit module/component identifier
- `.` = Separator
- `###` = Three-digit serial number

## Module Prefixes

- **A** = Application/Base errors
- **D** = Domain errors
- **E** = Data/Element errors
- **F** = Form errors
- **Q** = Query errors
- **P** = Navis/Workflow/Process errors
- **S** = Security/Auth errors

## Error Codes

### Application/Base Errors (A00.###)

| Code | Exception | Status | Description |
|------|-----------|--------|-------------|
| A00.000 | FluviusException | 500 | Base internal error |
| A00.401 | UnauthorizedError | 401 | Unauthorized request |
| A00.403 | ForbiddenError | 403 | Forbidden |
| A00.404 | NotFoundError | 404 | Not found |
| A00.412 | PreconditionFailedError | 412 | Precondition failed |
| A00.422 | UnprocessableError | 422 | Unprocessable entity |
| A00.423 | LockedError | 423 | Resource locked |
| A00.500 | InternalServerError | 500 | Internal server error |

### Domain Errors (D00.###)

| Code | Exception | Status | Description |
|------|-----------|--------|-------------|
| D00.001 | DomainEntityError | 400 | Domain entity validation error (exception class) |
| D00.001 | ForbiddenError | 403 | Action not allowed on resource (aggregate.py) |
| D00.002 | DomainEventValidationError | 400 | Domain event validation error (exception class) |
| D00.002 | ForbiddenError | 403 | Command does not allow aggroot of resource |
| D00.003 | DomainCommandValidationError | 400 | Domain command validation error (exception class) |
| D00.003 | ForbiddenError | 403 | Permission failed |
| D00.004 | CommandProcessingError | 500 | Command processing error |
| D00.005 | EventReceivingError | 500 | Event receiving error |
| D00.101 | DomainEntityError | 400 | Invalid resource specification |
| D00.101 | InternalServerError | 500 | Overlapping context |
| D00.102 | InternalServerError | 500 | All events must be consumed by command handler |
| D00.103 | InternalServerError | 500 | Aggregate context not initialized |
| D00.104 | InternalServerError | 500 | No command handler provided (domain.py) |
| D00.104 | InternalServerError | 500 | Aggregate context not initialized (aggregate.py) |
| D00.105 | InternalServerError | 500 | No message dispatcher provided (domain.py) |
| D00.105 | InternalServerError | 500 | Aggregate context not initialized (aggregate.py) |
| D00.106 | InternalServerError | 500 | Command has no handler |
| D00.107 | InternalServerError | 500 | Invalid command processor result |
| D00.108 | InternalServerError | 500 | Domain session not started |
| D00.109 | InternalServerError | 500 | Duplicated response |
| D00.110 | InternalServerError | 500 | Overlapping context (fixed duplicate) |
| D00.111 | InternalServerError | 500 | Aggregate context not initialized - aggroot property |
| D00.112 | InternalServerError | 500 | Aggregate context not initialized - command property |
| D00.201 | PreconditionFailedError | 412 | Un-matched document signatures |
| D00.201 | DomainEntityError | 400 | Domain already registered |
| D00.202 | DomainEntityError | 400 | Invalid domain aggregate |
| D00.203 | DomainEntityError | 400 | Domain already registered (fixed duplicate) |
| D00.204 | DomainEntityError | 400 | Invalid domain configuration |
| D00.205 | DomainEntityError | 400 | Invalid domain configuration |
| D00.206 | DomainEntityError | 400 | Invalid domain configuration |
| D00.207 | DomainEntityError | 400 | Invalid domain configuration |
| D00.208 | DomainEntityError | 400 | Invalid domain configuration |
| D00.301 | ForbiddenError | 403 | Action not allowed on resource (fixed duplicate) |
| D00.302 | ForbiddenError | 403 | Command does not allow aggroot of resource (fixed duplicate) |
| D00.303 | ForbiddenError | 403 | Permission failed (fixed duplicate) |

### Data/Element Errors (E00.###)

| Code | Exception | Status | Description |
|------|-----------|--------|-------------|
| E00.001 | UnprocessableError | 422 | Duplicate entry detected |
| E00.002 | UnprocessableError | 422 | Integrity constraint violated |
| E00.003 | UnprocessableError | 422 | Database unreachable |
| E00.004 | UnprocessableError | 422 | Database query syntax/structure error |
| E00.005 | UnprocessableError | 422 | DBAPIError occurred |
| E00.006 | ItemNotFoundError | 404 | Item not found (used in error handler decorator) |
| E00.007 | UnprocessableError | 422 | Unexpected database error |
| E00.101 | InternalServerError | 500 | AsyncSession connection not established |
| E00.102 | BadRequestError | 400 | Invalid URI |
| E00.103 | BadRequestError | 400 | Engine already setup |
| E00.104 | BadRequestError | 400 | No database DSN provided |
| E00.105 | BadRequestError | 400 | Schema only supports subclass |
| E00.106 | InternalServerError | 500 | Nested/concurrent transaction detected |
| E00.107 | InternalServerError | 500 | Database operation must be run in transaction |
| E00.108 | BadRequestError | 400 | Invalid find all query |
| E00.109 | BadRequestError | 400 | Invalid SQL query |
| E00.201 | BadRequestError | 400 | Invalid __automodel__ value |
| E00.202 | InternalServerError | 500 | Nested transaction detected |
| E00.203 | InternalServerError | 500 | State Manager context not initialized |
| E00.204 | BadRequestError | 400 | Invalid data driver/connector |
| E00.205 | BadRequestError | 400 | Invalid find_one query |
| E00.301 | BadRequestError | 400 | Invalid query statement |
| E00.302 | BadRequestError | 400 | Invalid query statement |
| E00.303 | BadRequestError | 400 | Invalid query operator statement |
| E00.304 | BadRequestError | 400 | Invalid list value |
| E00.305 | BadRequestError | 400 | Invalid query |
| E00.501 | BadRequestError | 400 | Type object has no attribute |
| E00.502 | BadRequestError | 400 | Invalid query expression |
| E00.503 | BadRequestError | 400 | Data schema does not support text search |
| E00.504 | BadRequestError | 400 | Unsupported values |
| E00.505 | BadRequestError | 400 | Invalid statement |

### Form Errors (F00.###)

| Code | Exception | Status | Description |
|------|-----------|--------|-------------|
| F00.001 | BadRequestError | 400 | No changes provided for collection update |
| F00.002 | BadRequestError | 400 | No changes provided for document update |
| F00.101 | BadRequestError | 400 | Element data validation failed |

### Query Errors (Q00.###)

| Code | Exception | Status | Description |
|------|-----------|--------|-------------|
| Q00.001 | BadRequestError | 400 | Scoping not allowed for resource (used in multiple places) |
| Q00.002 | ForbiddenError | 403 | Scoping required for resource (used in multiple places) |
| Q00.004 | ForbiddenError | 403 | Permission failed |
| Q00.005 | ForbiddenError | 403 | Policy meta must be str with jsonurl format |
| Q00.006 | InternalServerError | 500 | Internal error |
| Q00.501 | NotFoundError | 404 | Item not found |
| Q00.502 | BadRequestError | 400 | Text search not allowed for resource |
| Q00.503 | BadRequestError | 400 | Invalid list value |
| Q00.504 | BadRequestError | 400 | Invalid query value (fixed duplicate) |
| Q00.508 | BadRequestError | 400 | Invalid query |
| Q00.509 | BadRequestError | 400 | Scope required must include policy required field |
| Q00.510 | BadRequestError | 400 | Invalid query statement |
| Q00.511 | BadRequestError | 400 | Invalid query statement |
| Q00.512 | BadRequestError | 400 | Invalid query statement |
| Q00.513 | BadRequestError | 400 | QueryResource already registered |
| Q00.514 | BadRequestError | 400 | Resource identifier already registered |
| Q00.601 | BadRequestError | 400 | Preset already registered |
| Q00.602 | BadRequestError | 400 | Multiple default filters for preset |
| Q00.603 | BadRequestError | 400 | No default filter set for preset |
| Q00.604 | BadRequestError | 400 | Filter Preset does not exist (used in multiple methods) |
| Q00.605 | BadRequestError | 400 | Invalid input widget |
| Q00.606 | BadRequestError | 400 | Start date must be before end date |
| Q00.701 | BadRequestError | 400 | Resource already initialized |
| Q00.702 | BadRequestError | 400 | Multiple identifier for query resource |
| Q00.703 | BadRequestError | 400 | No identifier provided for query resource |
| Q00.704 | BadRequestError | 400 | Invalid sort statement |

### Navis/Workflow Errors (P00.###)

| Code | Exception | Status | Description |
|------|-----------|--------|-------------|
| P00.001 | WorkflowExecutionError | 422 | Unable to perform action outside transaction |
| P00.002 | WorkflowExecutionError | 422 | Unable to perform action at workflow status |
| P00.003 | WorkflowExecutionError | 422 | Unable to perform action at workflow status |
| P00.005 | WorkflowExecutionError | 422 | Workflow status not allowed (used in multiple contexts) |
| P00.006 | WorkflowExecutionError | 422 | Workflow at status not allowed to be updated (fixed duplicate) |
| P00.007 | WorkflowExecutionError | 422 | Cannot recover from a non-error status (fixed duplicate) |
| P00.008 | WorkflowExecutionError | 422 | Transition to state not allowed |
| P00.009 | WorkflowExecutionError | 422 | Transaction already started |
| P00.010 | WorkflowExecutionError | 422 | Mutation generated outside transaction |
| P00.011 | WorkflowConfigurationError | 422 | Step already registered |
| P00.012 | WorkflowConfigurationError | 422 | Stage not defined for workflow |
| P00.013 | WorkflowConfigurationError | 422 | Stage already defined with key |
| P00.014 | WorkflowConfigurationError | 422 | Stage already registered |
| P00.015 | WorkflowConfigurationError | 422 | Workflow has no steps after started |
| P00.015 | WorkflowConfigurationError | 422 | Role already registered |
| P00.016 | WorkflowConfigurationError | 422 | Role already registered (fixed duplicate) |
| P00.017 | WorkflowExecutionError | 422 | Step already exists |
| P00.021 | WorkflowConfigurationError | 422 | Invalid workflow definition |
| P00.031 | WorkflowConfigurationError | 422 | State not defined in Step states |
| P00.032 | WorkflowConfigurationError | 422 | Duplicated transition handler to state |
| P00.081 | NotFoundError | 404 | Event does not have handlers |
| P00.082 | NotFoundError | 404 | Step event must be routed to specific step |
| P00.083 | WorkflowConfigurationError | 422 | Event handler connected with step via step context |
| P00.101 | WorkflowExecutionError | 422 | No step available for selector value |
| P00.102 | WorkflowExecutionError | 422 | Invalid step states |
| P00.201 | BadRequestError | 400 | Workflow instance only available on workflow aggroot |
| P00.202 | BadRequestError | 400 | No changes provided for workflow update |
| P00.301 | BadRequestError | 400 | Activity already connected |
| P00.302 | BadRequestError | 400 | Invalid Workflow Event Router |
| P00.401 | BadRequestError | 400 | Invalid state |
| P00.402 | BadRequestError | 400 | Invalid step data |
| P00.501 | BadRequestError | 400 | Workflow already registered (manager.py) |
| P00.501 | InternalServerError | 500 | Invalid workflow state (runner.py) |
| P00.502 | InternalServerError | 500 | Invalid workflow state (fixed duplicate) |

### Security/Auth Errors (S00.###)

| Code | Exception | Status | Description |
|------|-----------|--------|-------------|
| S00.001 | BadRequestError | 400 | Invalid Auth Profile Provider |
| S00.002 | BadRequestError | 400 | Auth Profile Provider already registered |
| S00.003 | BadRequestError | 400 | Auth Profile Provider not valid |
| S00.004 | UnauthorizedError | 401 | Authorization failed |

## Notes

- All error codes are unique within their module prefix
- Error codes follow a consistent numbering scheme within each module
- ValueError and RuntimeError instances have been converted to proper FluviusException subclasses
- Error codes are prefixed with a single letter module identifier
- Some error codes may be used multiple times for the same error condition in different contexts (noted in descriptions)
- Duplicate error codes have been identified and fixed where they represent different error conditions

## Duplicate Error Codes (Fixed)

The following duplicate error codes were identified and resolved:

- **D00.001**: Split into D00.001 (DomainEntityError exception class) and D00.301 (ForbiddenError in aggregate)
- **D00.002**: Split into D00.002 (DomainEventValidationError exception class) and D00.302 (ForbiddenError in domain)
- **D00.003**: Split into D00.003 (DomainCommandValidationError exception class) and D00.303 (ForbiddenError in domain)
- **D00.101**: Split into D00.101 (DomainEntityError) and D00.110 (InternalServerError - overlapping context)
- **D00.104**: Split into D00.104 (domain.py) and D00.111 (aggregate.py - aggroot property)
- **D00.105**: Split into D00.105 (domain.py) and D00.112 (aggregate.py - command property)
- **D00.201**: Split into D00.201 (PreconditionFailedError) and D00.203 (DomainEntityError - domain registration)
- **P00.005**: Used in 3 contexts - kept first, changed others to P00.006 and P00.007
- **P00.015**: Split into P00.015 (workflow steps) and P00.016 (role registration)
- **P00.501**: Split into P00.501 (BadRequestError in manager) and P00.502 (InternalServerError in runner)
- **Q00.503**: Split into Q00.503 (invalid list value) and Q00.504 (invalid query value)

