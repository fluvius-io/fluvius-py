
from . import config
from .aggregate import AggregateRoot, ResourceReference
from .datadef import UUID_TYPE, UUID_GENR, identifier_factory, nullable, field
from .entity import CommandState, CQRS_ENTITY_MARKER
from .record import DomainEntityRecord, PayloadData
from .context import DomainContext


class CommandEnvelop(DomainEntityRecord):
    domain      = field(type=str, mandatory=True)
    command     = field(type=str, mandatory=True)
    revision    = field(type=int, mandatory=True)
    resource    = field(type=str, mandatory=True)
    identifier  = field(type=UUID_TYPE, mandatory=True, factory=identifier_factory)

    # Domain closure ID. The identifier to scope the item selection
    # in the case the identifier is duplicated (e.g. replication)
    # If domain cid is present, the aggroot is select by:
    # _iid = scope internal identifier (i.e. item identifier), _sid = domain scoping id
    domain_sid  = field(type=nullable(UUID_TYPE), factory=identifier_factory, initial=None)
    domain_iid  = field(type=nullable(UUID_TYPE), factory=identifier_factory, initial=None)

    context      = field(type=nullable(UUID_TYPE), factory=identifier_factory, initial=None)
    status      = field(type=CommandState, mandatory=True, initial=CommandState.CREATED)
    payload     = field(type=nullable(dict), initial=dict)

    def resource_reference(self, **kwargs):
        return ResourceReference(
            domain=self.domain,
            resource=self.resource,
            identifier=self.identifier,
            domain_sid=self.domain_sid,
            domain_iid=self.domain_iid,
            **kwargs
        )
    # @classmethod
    # def create(cls, _factory_fields=None, ignore_extra=config.IGNORE_COMMAND_EXTRA_FIELDS, **kwargs):
    #     ''' Factory method. Will create a new PRecord of the current type and assign the values
    #     specified in kwargs.
    #     :param ignore_extra: A boolean which when set to True will ignore any keys which appear in kwargs that are not
    #                          in the set of fields on the PRecord.
    #     '''

    #     if not hasattr(cls, CQRS_ENTITY_MARKER):
    #         raise TypeError("Cannot create un-cqrsified command. See [domain_entity]")

    #     if isinstance(kwargs, cls):
    #         return kwargs

    #     if ignore_extra:
    #         kwargs = {k: kwargs[k] for k in cls._pclass_fields if k in kwargs}

    #     return cls(
    #         _factory_fields=_factory_fields,
    #         **cls.defaults(),
    #         **kwargs
    #     )


class CommandEnvelopTemplate(CommandEnvelop):
    pass


class PendingCommand(CommandEnvelop):
    # @TODO: Clarify the usecase of this.
    stream_id = field(type=UUID_TYPE, factory=identifier_factory)


class ResourceCommand(CommandEnvelop):
    __target_resource__ = None

    def compute_selector(self):
        return self.aggroot.set(
            resource=self.__target_resource__,
            identifier=UUID_GENR()
        )


class Command(PayloadData):
    pass


__all__ = ("Command",)
