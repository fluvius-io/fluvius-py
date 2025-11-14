from fluvius.fastapi import (
    create_app,
    configure_authentication,
    configure_domain_manager,
    configure_query_manager)

from fluvius.form.domain import FormDomain
from fluvius.form.query import FormQueryManager
from fluvius.fastapi.auth_mock import FluviusMockProfileProvider

domains = (
    FormDomain,
)

queries = (
    FormQueryManager,
)

app = create_app() \
    | configure_authentication(auth_profile_provider=FluviusMockProfileProvider) \
    | configure_domain_manager(*domains) \
    | configure_query_manager(*queries)

