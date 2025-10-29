from fluvius.fastapi import (
    create_app,
    configure_authentication,
    configure_domain_manager,
    configure_query_manager)

from fluvius.nava.domain import WorkflowDomain, WorkflowQueryManager

domains = (
    WorkflowDomain,
)

queries = (
    WorkflowQueryManager,
)

app = create_app() \
    | configure_authentication() \
    | configure_domain_manager(*domains) \
    | configure_query_manager(*queries) 
