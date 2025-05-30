from fluvius.fastapi import create_app, configure_authentication, configure_domain_manager, configure_query_manager
from .main import configure_sample_app

app = create_app() \
    | configure_authentication() \
    | configure_domain_manager('object_domain.domain.ObjectDomain') \
    | configure_query_manager(
        'fastapi_app.main.SampleQueryManager',
        'object_domain.query.ObjectDomainQueryManager') \
    | configure_sample_app()



