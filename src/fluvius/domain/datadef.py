# from enum import IntEnum
# from datetime import datetime
# from fluvius.data import timestamp, config, logger  # noqa
# from fluvius.helper.timeutil import parse_iso_datestring

# from fluvius.data.helper import nullable as nullable_type, nullable, generate_etag
# from fluvius.data.identifier import UUID_TYPE, identifier_factory, UUID_GENR, UUID_GENF
# from fluvius.data.query import BackendQuery
# from fluvius.data.serializer import serialize_mapping
# from fluvius.data.data_model import DataModel


# DomainDataModel = PClass


# def enum_serializer(obj, field):
#     return field.value


# def EnumField(enum_type, nullable=False, **kwargs):
#     if nullable:
#         enum_type = nullable_type(enum_type)

#     return field(enum_type, factory=enum_type, serializer=enum_serializer)


# def UUIDField(nullable=False, **kwargs):
#     _type = UUID_TYPE if not nullable else nullable_type(UUID_TYPE)

#     return field(_type, factory=identifier_factory, **kwargs)


# def DateTimeField(nullable=False, **kwargs):
#     _type = datetime if not nullable else nullable_type(datetime)
#     return field(_type, factory=parse_iso_datestring, **kwargs)


# def PrimaryIDField(**kwargs):
#     return field(type=UUID_TYPE, factory=identifier_factory, initial=UUID_GENR, mandatory=True)


# class DomainResource(DomainDataModel):
#     _id      = field(type=UUID_TYPE, initial=UUID_GENR)
#     _created = field(datetime, mandatory=True, initial=timestamp)
#     _updated = field(datetime, mandatory=True, initial=timestamp)
#     _creator = field(nullable(UUID_TYPE))
#     _updater = field(nullable(UUID_TYPE))
#     _deleted = field(nullable(datetime))
#     _etag    = field(nullable(str), mandatory=True, initial=None)


# class DomainSubResource(DomainResource):
#     _sid = field(type=UUID_TYPE, factory=identifier_factory, mandatory=True)
#     _iid = field(type=UUID_TYPE, factory=identifier_factory, mandatory=True)


# class DomainResourcePropertySchema(IntEnum):
#     WORKFLOW_PARAMETER = 1
#     WORKFLOW_MEMORY = 2


# class DomainResourceProperty(DomainResource):
#     _schema = None

#     def __init_subclass__(cls):
#         if not isinstance(cls._schema, DomainResourcePropertySchema):
#             raise ValueError('No schema (_schema) provided for resource property: %s' % str(cls))

#     ref_id = UUIDField()
#     key = field(type=str, mandatory=True)
#     value = field(type=nullable(str))
#     note = field(type=nullable(str))
#     scope = UUIDField(nullable=True)
#     schema = field(type=int)

#     def serialize(self):
#         data = super().serialize()
#         data['schema'] = self._schema
#         return data


# class ResourcePropertyFieldSchema(DomainResource):
#     schema = field(type=int)
#     key = field(type=str, mandatory=True)
#     name = field(type=str)
#     desc = field(type=str)
#     dtype = field(type=int)
#     group = field(type=str)
#     validator = field(type=str)


# class ResourceReference(DomainDataModel):
#     identifier = field(type=nullable(UUID_TYPE), factory=identifier_factory, mandatory=True)
#     resource = field(type=str, mandatory=True)

#     # Domain scoping ID / i.e. _sid. This ID is used to scoping changes within a domain.
#     domain_sid = field(type=nullable(UUID_TYPE), factory=identifier_factory)
#     domain_iid = field(type=nullable(UUID_TYPE), factory=identifier_factory)
#     domain = field(type=nullable(str))
#     dataset_id = field(type=str)
#     match_etag = field(type=str)


# AggregateRoot = ResourceReference
