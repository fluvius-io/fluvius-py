from account_transaction.domain import TransactionManagerDomain
from fluvius.domain.record import field
from fluvius.domain.response import DomainResponse
from fluvius.domain.message import DomainMessage


_entity = TransactionManagerDomain.entity
_command_processor = TransactionManagerDomain.command_processor


@_entity
class GeneralResponse(DomainResponse):
    data = field(type=dict, mandatory=True)


@_entity
class GeneralMessage(DomainMessage):
    data = field(type=dict)
