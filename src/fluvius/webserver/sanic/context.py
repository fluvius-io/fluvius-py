from fluvius.domain.context import DomainContext, DomainServiceProxy
from fluvius.domain.datadef import field


class SanicDomainServiceProxy(DomainServiceProxy):
    ''' To filter the functionaly that will be exposed to CQRS handlers '''

    def __init__(self, app):
        super(SanicDomainServiceProxy, self).__init__(app)
        self._mqtt_client = getattr(app.ctx, 'mqtt_client', None)
        self._arq_client = getattr(app.ctx, 'arq_client', None)
        self._lightq = getattr(app.ctx, 'lightq', None)
        self._brokerage_client = getattr(app.ctx, 'brokerage_client', None)


class SanicContext(DomainContext):
    _session = field()

    @property
    def session(self):
        return self._session
