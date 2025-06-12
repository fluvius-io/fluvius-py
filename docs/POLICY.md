# Fluvius Policy Manager

A sophisticated policy management system built on Casbin for handling fine-grained access control in Fluvius.

## Overview

The Fluvius Policy Manager provides a robust, flexible, and efficient access control system with the following key features:

- Role-Based Access Control (RBAC) with multi-level scoping
- Organization and domain-scoped permissions
- Resource-level access control
- Read-only policy enforcement
- Filtered policy loading for memory efficiency
- SQL-based policy storage using Fluvius data driver
- Support for both system-wide and organization-specific roles
- Detailed policy narration and explanation

## Core Components

### 1. Policy Model

The policy model is defined with several key elements:

#### Request Definition
```
r = usr, sub, org, dom, res, rid, act
```
- `usr`: User ID
- `sub`: Profile ID
- `org`: Organization ID
- `dom`: Domain name
- `res`: Resource type
- `rid`: Resource ID
- `act`: Action to perform

#### Policy Definition
```
p = role, dom, res, act, cqrs, meta
```
- `role`: Role name
- `dom`: Domain scope
- `res`: Resource type
- `act`: Permitted action
- `cqrs`: Command/Query type
- `meta`: Additional metadata (JSON-URL format)

#### Role Mappings
```
# Organization Scope
g = _, _, _    # (subject, role, org)
g2 = _, _, _   # (org, resource, resource_id)

# User Scope
g3 = _, _      # (user, role)
g4 = _, _, _   # (user, resource, resource_id)
```

### 2. Policy Manager

```python
from fluvius.casbin import PolicyManager, PolicyRequest

class CustomPolicyManager(PolicyManager):
    __table__ = "policy_table"
    __model__ = "path/to/model.conf"

# Initialize
policy_manager = CustomPolicyManager(data_access_manager)

# Check permissions
request = PolicyRequest(
    usr="user_123",
    sub="profile_456",
    org="org_789",
    dom="project",
    res="document",
    rid="doc_001",
    act="edit"
)

response = await policy_manager.check_permission(request)
```

### 3. Database Schema (PolicySchema)

```sql
CREATE TABLE policy_table (
    _id UUID PRIMARY KEY,
    ptype VARCHAR(255),      -- Policy type (p, g, g2, g3, g4)
    role VARCHAR(255),       -- Role name
    sub VARCHAR(255),        -- Subject/Profile ID
    org VARCHAR(255),        -- Organization ID
    dom VARCHAR(255),        -- Domain
    res VARCHAR(255),        -- Resource type
    rid VARCHAR(255),        -- Resource ID
    act VARCHAR(255),        -- Action
    cqrs VARCHAR(255),       -- Command/Query type
    meta VARCHAR(1000),      -- Metadata
    _deleted TIMESTAMP       -- Soft delete timestamp
);
```

## Usage Examples

### 1. Basic Permission Check

```python
# Check if a user can perform an action
response = await policy_manager.check(
    "user_123",      # usr
    "profile_456",   # sub
    "org_789",       # org
    "project",       # dom
    "document",      # res
    "doc_001",       # rid
    "edit"          # act
)

if response.allowed:
    print(f"Access granted: {response.narration}")
else:
    print(f"Access denied: {response.narration}")
```

### 2. Policy Rules Examples

```
# System admin role
p, sys-admin, *, *, *, *, *

# Organization admin for project domain
p, org-admin, project, *, *, *, {"conditions": "org_id={org}"}

# Project viewer role
p, project-viewer, project, document, view, query, {"resource_id": "{rid}"}

# Role assignments
g, profile_123, org-admin, org_789    # Assign org-admin role to profile in org
g3, user_456, sys-admin               # Assign system-wide admin role to user
g2, org_789, document, doc_001        # Grant org access to specific document
g4, user_123, document, doc_001       # Grant user access to specific document
```

## Advanced Features

### 1. Policy Filtering

The PolicyManager supports filtered policy loading to prevent loading all policies into memory:

```python
# Policies are automatically filtered by organization
await policy_manager.load_filtered_policy({"org": "org_789"})
```

### 2. Policy Narration

Each policy decision includes detailed narration explaining why access was granted or denied:

```python
response = await policy_manager.check_permission(request)
print(response.narration.message)
for policy in response.narration.policies:
    print(f"Applied policy: {policy}")
```

### 3. Integration with Query System

The PolicyManager integrates with Fluvius's query system for automatic permission checking:

```python
query_manager = QueryManager(policy_manager=policy_manager)
await query_manager.authorize_by_policy(resource, query, auth_context)
```

## Security Considerations

1. **Read-Only Design**: The PolicyManager is intentionally read-only to prevent runtime policy modifications.
2. **Memory Efficiency**: Uses filtered policy loading to prevent loading unnecessary policies.
3. **Soft Deletion**: Supports soft deletion of policies via `_deleted` timestamp.
4. **Fine-grained Control**: Supports both broad and specific permissions through resource IDs.
5. **Organization Isolation**: Policies are scoped to organizations by default.

## Best Practices

1. **Role Design**:
   - Use system-wide roles (`g3`) sparingly
   - Prefer organization-scoped roles (`g`) for most cases
   - Use resource grants (`g2`, `g4`) for fine-grained control

2. **Performance**:
   - Keep policy rules focused and specific
   - Use filtered policy loading when possible
   - Index frequently queried policy fields

3. **Maintenance**:
   - Document policy rules and their purposes
   - Regularly audit policy assignments
   - Use meaningful role names and consistent naming conventions

4. **Error Handling**:
   - Always check policy responses
   - Log policy decisions for audit purposes
   - Handle permission denied cases gracefully

## Troubleshooting

Common issues and solutions:

1. **Permission Denied Unexpectedly**:
   - Check role assignments (g, g2, g3, g4 relations)
   - Verify organization and domain matches
   - Check resource ID grants

2. **Performance Issues**:
   - Enable filtered policy loading
   - Index frequently queried fields
   - Review policy rule complexity

3. **Policy Not Loading**:
   - Verify database connection
   - Check table schema matches PolicySchema
   - Ensure policy file format is correct 