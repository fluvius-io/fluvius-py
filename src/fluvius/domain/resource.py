from fluvius.domain.record import DomainEntityRecord
from .entity import DOMAIN_ENTITY_MARKER


class DomainResource(DomainEntityRecord):
    def serialize(self):
        key, kind, *_ = getattr(self.__class__, DOMAIN_ENTITY_MARKER)
        data = super().serialize()
        data.update(_domain=key, _kind=kind, _vers=self._version)
        return data
