from fluvius.fastapi import (
    create_app,
    configure_authentication,
    configure_domain_manager,
    configure_query_manager)

from fluvius.navis.domain import WorkflowDomain, WorkflowQueryManager
from fluvius.fastapi.auth_mock import FluviusMockProfileProvider

domains = (
    WorkflowDomain,
)

queries = (
    WorkflowQueryManager,
)

app = create_app() \
    | configure_authentication(auth_profile_provider=FluviusMockProfileProvider) \
    | configure_domain_manager(*domains) \
    | configure_query_manager(*queries)
