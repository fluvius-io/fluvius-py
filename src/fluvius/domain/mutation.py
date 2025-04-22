from datetime import datetime
from enum import Enum
from fluvius.data.helper import nullable
from fluvius.data import UUID_TYPE, BackendQuery, serialize_mapping, PClass, field


def validate_data_record(data):
    if data is None:
        return data

    if not isinstance(data, DataRecord):
        raise ValueError('Invalid DataRecord: %s' % data)

    return data


def DataRecordField(**kwargs):
    return field(factory=validate_data_record, mandatory=True, **kwargs)


def BackendQueryField(**kwargs):
    return field(nullable(BackendQuery), **kwargs)


class UpdatedTrail(PClass):
    _updated = field(datetime)
    _updater = field(UUID_TYPE)
    _etag = field(str)


class CreatedTrail(PClass):
    _updated = field(datetime)
    _updater = field(UUID_TYPE)
    _created = field(datetime)
    _creator = field(UUID_TYPE)
    _etag = field(str)


class MutationType(Enum):
    ''' WARNING: Maintain strict order!
        This will is the persisting order of state managers '''
    RECORD_MUTATION  = 'record_mutation'
    MULTI_MUTATION = 'multi_mutation'
    BATCH_MUTATION = 'batch_mutation'
    BATCH_VERIFIED_MUTATION = 'batch_verified'


class StateMutation(PClass):
    @property
    def kind(self):
        return self._kind


class InvalidMutationError(Exception):
    pass


class NullMutationError(InvalidMutationError):
    pass


class ItemStateMutation(StateMutation):
    _kind = MutationType.RECORD_MUTATION

    identifier = field(UUID_TYPE, mandatory=True)
    resource = field(type=str, mandatory=True)
    original = field()
    etag = field(nullable(str), initial=None, mandatory=True)
    note = field()
    record = DataRecordField()
    audit = field(dict, mandatory=True)
    data = field(type=dict, factory=serialize_mapping, mandatory=True, initial=dict)


class InsertRecord(ItemStateMutation):
    pass


class UpsertRecord(ItemStateMutation):
    pass


class UpdateRecord(ItemStateMutation):
    pass


class InvalidateRecord(ItemStateMutation):
    data = field(type=dict, factory=serialize_mapping, initial=dict)


class RemoveRecord(ItemStateMutation):
    data = field(type=nullable(dict), factory=serialize_mapping)


class MultiItemMutation(ItemStateMutation):
    _kind = MutationType.MULTI_MUTATION
    resource = field(type=str, mandatory=True)
    items = field(type=list, mandatory=True)
    audit = field(dict)


class UpsertMultiRecord(MultiItemMutation):
    pass


class InsertMultiRecord(MultiItemMutation):
    audit = field(dict)


class UpdateMultiRecord(MultiItemMutation):
    pass


class InvalidateMultiRecord(MultiItemMutation):
    pass


class RemoveMultiRecord(MultiItemMutation):
    pass


class BatchStateMutation(StateMutation):
    _kind = MutationType.BATCH_MUTATION
    resource = field(type=str, mandatory=True)
    query = BackendQueryField(mandatory=True)
    audit = field(dict)


class RemoveRecordBatch(BatchStateMutation):
    pass


class InvalidateRecordBatch(BatchStateMutation):
    data = field(type=dict, factory=serialize_mapping, mandatory=True, initial={})


class UpdateRecordBatch(StateMutation):
    data = field(type=dict, factory=serialize_mapping, mandatory=True, initial={})
