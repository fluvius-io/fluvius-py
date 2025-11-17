from fluvius.fastapi import (
    create_app,
    configure_authentication,
    configure_domain_manager,
    configure_query_manager)

from fluvius.navis.domain import WorkflowDomain, WorkflowQueryManager
from fluvius.fastapi.auth_mock import FluviusMockProfileProvider

# Import the loan application process workflow
from . import process

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

from posthog import Posthog

posthog = Posthog(
  project_api_key='phc_3gftHoN1M0lnMjxmzUDxCFXEmuBNsRFAvev1PNJxzeB',
  host='https://us.i.posthog.com'
)

posthog.capture("user_signed_up", properties={"example_property": "with_some_value"})
