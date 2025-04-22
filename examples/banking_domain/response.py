from account_transaction.domain import TransactionManagerDomain
from fluvius.domain.record import field
from fluvius.domain.response import DomainResponse
from fluvius.domain.message import MessageBundle


_entity = TransactionManagerDomain.entity
_command_processor = TransactionManagerDomain.command_processor


@_entity
class GeneralResponse(DomainResponse):
    data = field(type=dict, mandatory=True)


@_entity
class GeneralMessage(MessageBundle):
    data = field(type=dict)
