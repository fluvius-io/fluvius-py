# Fluvius Policy Manager

A Casbin-based policy management system for handling access control in Fluvius.

## Features

- Role-based access control (RBAC) with domains
- Organization and domain-scoped permissions
- Resource-level access control
- Read-only policy enforcement
- Filtered policy loading for memory efficiency
- SQL-based policy storage using Fluvius data driver

## Usage

```python
from fluvius.casbin.policy_manager import PolicyManager, PolicyRequest
from fluvius.data.driver import DataDriver

# Initialize
data_driver = DataDriver(...)  # Your data driver instance
policy_manager = PolicyManager(
    data_driver=data_driver,
    schema="your_schema",
    table="policy_table"
)
await policy_manager.initialize()

# Check permissions
request = PolicyRequest(
    profile="profile_123",
    org="org_456",
    domain="project",
    action="create-project",
    resource="project",
    resource_id="*"
)

response = await policy_manager.check_permission(request)
if response.allowed:
    print(f"Access granted: {response.narration}")
else:
    print(f"Access denied: {response.narration}")

# Get roles for a profile
roles = await policy_manager.get_roles("profile_123", "org_456", "project")

# Get policies for a role
policies = await policy_manager.get_policies("admin", "project")
```

## Policy Model

The policy model is defined in `model.conf` and supports:

- Profile-based access control
- Organization scoping
- Domain-specific roles
- Resource-level permissions
- Action-based access control

### Policy Structure

1. Profile to Role mapping:
```
p = profile, org, domain, role
```

2. Role to Permission mapping:
```
p2 = role, domain, action, resource, resource_id
```

### Example Policies

```
# Assign admin role to profile
p, profile_123, org_456, project, admin

# Define admin permissions
p2, admin, project, create-project, project, *
p2, admin, project, view-project, project, *
p2, admin, project, update-project, project, *
```

## Database Schema

The policy table should have the following columns:

- ptype (varchar): Policy type (p, p2, g)
- v0 (varchar): First value (profile/role)
- v1 (varchar): Second value (org/domain)
- v2 (varchar): Third value (domain/action)
- v3 (varchar): Fourth value (role/resource)
- v4 (varchar): Fifth value (resource_id)
- v5 (varchar): Sixth value (optional)

## Notes

- The PolicyManager is read-only by design
- Policies are loaded with filtering to prevent memory issues
- Uses the Fluvius data driver for database access
- Supports both query and command actions
- Returns detailed narration for policy decisions 