from .record import DomainEntityRecord, field


class Session(DomainEntityRecord):
    _id = field()
