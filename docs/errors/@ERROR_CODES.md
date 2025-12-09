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
- **T** = Transform/Data Mapping (dmap) errors
- **C** = Casbin errors
- **R** = Ordinis/Rule errors
- **W** = Worker errors
- **M** = Media errors
- **H** = Helper errors

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
| F00.102 | BadRequestError | 400 | ElementData subclass must define a Meta class |
| F00.103 | BadRequestError | 400 | ElementData subclass Meta must define type_key |
| F00.104 | BadRequestError | 400 | ElementData subclass Meta must define type_name |
| F00.201 | NotFoundError | 404 | Target collection not found |
| F00.202 | NotFoundError | 404 | Source collection not found |

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
| S00.101 | BadRequestError | 400 | Password must be either a string or bytes (hashes.py) |
| S00.102 | BadRequestError | 400 | Invalid authentication token (auth.py) |
| S00.103 | UnauthorizedError | 401 | Authentication failed (auth.py) |
| S00.104 | BadRequestError | 400 | Invalid authentication header (auth.py) |
| S00.201 | BadRequestError | 400 | Invalid mock authorization header (auth_mock.py) |
| S00.202 | BadRequestError | 400 | Path elements must not start with / (helper.py) |
| S00.203 | BadRequestError | 400 | Please input a valid email (kcadmin.py) |
| S00.301 | InternalServerError | 500 | Domain manager already initialized (domain.py) |
| S00.401 | BadRequestError | 400 | Keycloak token error (kcadmin.py) |
| S00.402 | BadRequestError | 400 | Error request to Keycloak (kcadmin.py) |
| S00.403 | ForbiddenError | 403 | Email not allowed (whitelist check) (kcadmin.py) |
| S00.404 | ForbiddenError | 403 | Email not allowed (blacklist check) (kcadmin.py) |

### Transform/Data Mapping Errors (T00.###)

| Code | Exception | Status | Description |
|------|-----------|--------|-------------|
| T00.101 | BadRequestError | 400 | Writer of type not supported |
| T00.102 | BadRequestError | 400 | Transformer of type not supported |
| T00.201 | BadRequestError | 400 | Value is not a list |
| T00.202 | BadRequestError | 400 | Invalid writer config |
| T00.301 | BadRequestError | 400 | DataProcessManager already registered |
| T00.302 | BadRequestError | 400 | DataProcessManager not registered |
| T00.401 | BadRequestError | 400 | Invalid mapping spec |
| T00.402 | BadRequestError | 400 | No reducer specified yet there are multiple values |
| T00.501 | BadRequestError | 400 | Invalid transformers spec |
| T00.502 | BadRequestError | 400 | Invalid transformer |
| T00.503 | BadRequestError | 400 | Duplicated transformers key |
| T00.601 | BadRequestError | 400 | Reducer already registered |
| T00.602 | BadRequestError | 400 | Reducer has not been registered |
| T00.701 | BadRequestError | 400 | Coercer already registered |
| T00.702 | BadRequestError | 400 | Coercer has not been registered |
| T00.801 | BadRequestError | 400 | Coercer do not support parameterization |
| T00.901 | BadRequestError | 400 | Data type is not supported |
| T00.111 | BadRequestError | 400 | Reader of type not supported |
| T00.112 | BadRequestError | 400 | Reader key already registered |
| T00.121 | BadRequestError | 400 | Pipeline is set already |
| T00.122 | BadRequestError | 400 | Inconsistent headers |
| T00.123 | BadRequestError | 400 | No extension provided for current writer |
| T00.131 | BadRequestError | 400 | Datasource already registered |
| T00.141 | BadRequestError | 400 | Endpoint field must be set |
| T00.142 | BadRequestError | 400 | Request argument must be instances of class APIFetcherRequest |
| T00.143 | BadRequestError | 400 | Method is not supported |
| T00.151 | BadRequestError | 400 | Both user supplied args and config paths are provided |
| T00.161 | BadRequestError | 400 | Invalid try_sheets values |
| T00.162 | BadRequestError | 400 | No worksheets matches sheet selector |
| T00.171 | BadRequestError | 400 | Table name must have schema prefixed |
| T00.181 | BadRequestError | 400 | Cannot generate data of type |
| T00.191 | BadRequestError | 400 | Readers have different variant |

### Casbin Errors (C00.###)

| Code | Exception | Status | Description |
|------|-----------|--------|-------------|
| C00.101 | ForbiddenError | 403 | Model is undefined |
| C00.102 | BadRequestError | 400 | Invalid request size |
| C00.103 | ForbiddenError | 403 | Invalid policy size |
| C00.104 | ForbiddenError | 403 | Matcher result should be bool, int or float |
| C00.105 | BadRequestError | 400 | Please make sure rule exists in policy when using eval() in matcher |
| C00.201 | BadRequestError | 400 | __adapter__ is required |
| C00.202 | BadRequestError | 400 | __schema__ is required for Custom like SQLAdapter |
| C00.203 | BadRequestError | 400 | Permission check failed |
| C00.204 | BadRequestError | 400 | Failed to parse policy meta |
| C00.205 | BadRequestError | 400 | Failed to render value |
| C00.301 | BadRequestError | 400 | Unsupported policy type |

### Ordinis Errors (R00.###)

| Code | Exception | Status | Description |
|------|-----------|--------|-------------|
| R00.101 | BadRequestError | 400 | Cannot change WorkingMemory reserved attributes |
| R00.102 | InternalServerError | 500 | Reading callable attributes is not allowed |
| R00.201 | BadRequestError | 400 | Invalid Narration |

### Worker Errors (W00.###)

| Code | Exception | Status | Description |
|------|-----------|--------|-------------|
| W00.101 | BadRequestError | 400 | Server and client must not in the same queue |
| W00.102 | BadRequestError | 400 | Invalid worker tracker |
| W00.103 | BadRequestError | 400 | Loop back detected |
| W00.201 | BadRequestError | 400 | Function is not a coroutine |
| W00.301 | BadRequestError | 400 | Invalid job handle |
| W00.302 | BadRequestError | 400 | Redis pool is already opened |
| W00.303 | BadRequestError | 400 | Invalid worker configuration |

### Media Errors (M00.###)

| Code | Exception | Status | Description |
|------|-----------|--------|-------------|
| M00.101 | NotFoundError | 404 | Filesystem not found |
| M00.201 | NotFoundError | 404 | MediaEntry not found |
| M00.202 | NotFoundError | 404 | MediaFilesystem not found |
| M00.203 | BadRequestError | 400 | Mock model not supported |
| M00.301 | BadRequestError | 400 | Compression method already registered |
| M00.302 | BadRequestError | 400 | Compression method not supported |
| M00.401 | InternalServerError | 500 | Failed to compress data with GZIP |
| M00.402 | InternalServerError | 500 | Failed to decompress GZIP data |
| M00.403 | InternalServerError | 500 | Failed to open GZIP compressed data |
| M00.404 | InternalServerError | 500 | Failed to compress stream with GZIP |
| M00.501 | InternalServerError | 500 | Failed to compress data with BZ2 |
| M00.502 | InternalServerError | 500 | Failed to decompress BZ2 data |
| M00.503 | InternalServerError | 500 | Failed to open BZ2 compressed data |
| M00.504 | InternalServerError | 500 | Failed to compress stream with BZ2 |
| M00.601 | InternalServerError | 500 | Failed to compress data with LZMA |
| M00.602 | InternalServerError | 500 | Failed to decompress LZMA data |
| M00.603 | InternalServerError | 500 | Failed to open LZMA compressed data |
| M00.604 | InternalServerError | 500 | Failed to compress stream with LZMA |

### Helper Errors (H00.###)

| Code | Exception | Status | Description |
|------|-----------|--------|-------------|
| H00.101 | BadRequestError | 400 | Invalid lower-dash identifier |
| H00.201 | BadRequestError | 400 | Both user value and class value provided |
| H00.202 | BadRequestError | 400 | Value is required |
| H00.301 | BadRequestError | 400 | Register a class with a different key is not allowed |
| H00.302 | BadRequestError | 400 | Key already registered in registry |
| H00.303 | BadRequestError | 400 | Registering class must be a subclass |
| H00.401 | NotFoundError | 404 | Registry item not found in registry |
| H00.501 | BadRequestError | 400 | Invalid date string |
| H00.502 | BadRequestError | 400 | Invalid date object |
| H00.503 | BadRequestError | 400 | Invalid iso datetime string |
| H00.601 | BadRequestError | 400 | c_profiler is not working properly with generator/async function |

## Notes

- All error codes are unique within their module prefix
- Error codes follow a consistent numbering scheme within each module
- ValueError and RuntimeError instances have been converted to proper FluviusException subclasses
- Error codes are prefixed with a single letter module identifier
- Some error codes may be used multiple times for the same error condition in different contexts (noted in descriptions)
- Duplicate error codes have been identified and fixed where they represent different error conditions
