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

## Error Codes

### Application/Base Errors (A00.###)

| Code | Exception | Status | Description |
|------|-----------|--------|-------------|
| A00.000 | FluviusException | 500 | Base internal error |
| A00.400 | BadRequestError | 400 | Bad request |
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
| D00.001 | DomainEntityError | 400 | Domain entity validation error |
| Domain entity validation error |
| D00.002 | DomainEventValidationError | 400 | Domain event validation error |
| D00.003 | DomainCommandValidationError | 400 | Domain command validation error |
| D00.004 | CommandProcessingError | 500 | Command processing error |
| D00.005 | EventReceivingError | 500 | Event receiving error |
| D00.001 | ForbiddenError | 403 | Action not allowed on resource |
| D00.002 | ForbiddenError | 403 | Command does not allow aggroot of resource |
| D00.003 | ForbiddenError | 403 | Permission failed |
| D00.101 | DomainEntityError | 400 | Invalid resource specification |
| D00.102 | InternalServerError | 500 | All events must be consumed by command handler |
| D00.103 | InternalServerError | 500 | Aggregate context not initialized |
| D00.104 | InternalServerError | 500 | No command handler provided |
| D00.105 | InternalServerError | 500 | No message dispatcher provided |
| D00.106 | InternalServerError | 500 | Command has no handler |
| D00.107 | InternalServerError | 500 | Invalid command processor result |
| D00.108 | InternalServerError | 500 | Domain session not started |
| D00.109 | InternalServerError | 500 | Duplicated response |
| D00.201 | PreconditionFailedError | 412 | Un-matched document signatures |
| D00.101 | InternalServerError | 500 | Overlapping context |
| D00.301 | BadRequestError | 400 | IF-MATCH header required |

### Data/Element Errors (E00.###)

| Code | Exception | Status | Description |
|------|-----------|--------|-------------|
| E00.001 | UnprocessableError | 422 | Duplicate entry detected |
| E00.002 | UnprocessableError | 422 | Integrity constraint violated |
| E00.003 | UnprocessableError | 422 | Database unreachable |
| E00.004 | UnprocessableError | 422 | Database query syntax/structure error |
| E00.005 | UnprocessableError | 422 | DBAPIError occurred |
| E00.006 | ItemNotFoundError | 404 | Item not found |
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
| Q00.001 | BadRequestError | 400 | Scoping not allowed for resource |
| Q00.002 | ForbiddenError | 403 | Scoping required for resource |
| Q00.003 | BadRequestError | 400 | Cannot locate operator |
| Q00.004 | ForbiddenError | 403 | Permission failed |
| Q00.005 | ForbiddenError | 403 | Policy meta must be str with jsonurl format |
| Q00.006 | InternalServerError | 500 | Internal error |
| Q00.007 | UnauthorizedError | 401 | Authorization failed: Missing/invalid claims token |
| Q00.501 | NotFoundError | 404 | Item not found |
| Q00.502 | BadRequestError | 400 | Text search not allowed for resource |
| Q00.503 | BadRequestError | 400 | Invalid list/query value |

### Navis/Workflow Errors (P00.###)

| Code | Exception | Status | Description |
|------|-----------|--------|-------------|
| P00.001 | WorkflowExecutionError | 422 | Unable to perform action outside transaction |
| P00.002 | WorkflowExecutionError | 422 | Unable to perform action at workflow status |
| P00.003 | WorkflowExecutionError | 422 | Unable to perform action at workflow status |
| P00.005 | WorkflowExecutionError | 422 | Workflow status not allowed |
| P00.007 | WorkflowExecutionError | 422 | Transition to state limited |
| P00.008 | WorkflowExecutionError | 422 | Transition to state not allowed |
| P00.009 | WorkflowExecutionError | 422 | Transaction already started |
| P00.010 | WorkflowExecutionError | 422 | Mutation generated outside transaction |
| P00.011 | WorkflowConfigurationError | 422 | Step already registered |
| P00.012 | WorkflowConfigurationError | 422 | Stage not defined for workflow |
| P00.013 | WorkflowConfigurationError | 422 | Stage already defined with key |
| P00.014 | WorkflowConfigurationError | 422 | Stage already registered |
| P00.015 | WorkflowConfigurationError | 422 | Role already registered / Workflow has no steps |
| P00.016 | WorkflowExecutionError | 422 | Mutation only allowed by workflow actions |
| P00.017 | WorkflowExecutionError | 422 | Step already exists |
| P00.021 | WorkflowConfigurationError | 422 | Invalid workflow definition |
| P00.031 | WorkflowConfigurationError | 422 | State not defined in Step states |
| P00.032 | WorkflowConfigurationError | 422 | Duplicated transition handler to state |
| P00.081 | NotFoundError | 404 | Event does not have handlers |
| P00.082 | NotFoundError | 404 | Step event must be routed to specific step |
| P00.083 | WorkflowConfigurationError | 422 | Event handler connected with step via step context |
| P00.101 | WorkflowExecutionError | 422 | No step available for selector value |
| P00.102 | WorkflowExecutionError | 422 | Invalid step states |

## Notes

- All error codes are unique within their module prefix
- Error codes follow a consistent numbering scheme within each module
- ValueError and RuntimeError instances have been converted to proper FluviusException subclasses
- Error codes are prefixed with a single letter module identifier

