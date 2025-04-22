# 2024-04-01

https://github.com/jsonurl/specification/


# DOMAIN & IDENIFIERS


IDENTIFIER ~
    The identifier of an object is the **globally unique** ID to identify the object in the table

RESOURCE ~
    Indicate the type of the object

DOMAIN_SID ~
    Domain Scope ID is the identifier of the scoping (i.e. replication root) of the object
    Domain Scope ID can also be used to create replicated dataset
    Only primary object (i.e. object without Domain Scope ID) can be replicated

DOMAIN_IID ~
    Domain Internal ID is the identifier of the original object that is the source of the current object



## URL PATTERNS

### Query:

Default:        `/<domain_namespace>~<query_id>/`
Scoped:         `/<domain_namespace>~<query_id>/sid=66c8fd6c-0a5d-4bca-a86d-37756821a94b/`
Item:           `/<domain_namespace>~<query_id>/<identifier>`
Item Scoped:    `/<domain_namespace>~<query_id>/sid=66c8fd6c0a5d4bcaa86d37756821a94b/<identifier>`


### Command:

Default (NoID): `/<domain_namespace>:<command_id>/<resource>/`
Default:        `/<domain_namespace>:<command_id>/<resource>/<identifier>`
Scoped (NoID):  `/<domain_namespace>:<command_id>/sid=39129912/<resource>/`
Scoped:         `/<domain_namespace>:<command_id>/sid=39129912/<resource>/<identifier>`
