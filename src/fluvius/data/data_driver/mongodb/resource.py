from fluvius.domain.resource import DomainResource
from sanic_motor import BaseModel


class InvalidResourceBackend(ValueError):
    pass


class CheckMongoBackendMetaclass(DomainResource.__class__):
    def __init__(cls, name, bases, clsdict):
        if bases[0] != DomainResource:
            try:
                backend = getattr(cls, '__backend__')
                if not (issubclass(backend, BaseModel) and backend != BaseModel):
                    raise ValueError('Invalid backend')
            except (ValueError, TypeError, AttributeError):
                raise InvalidResourceBackend(
                    f'Invalid __backend__ for: {cls.__name__} [{backend}].'
                    ' It must be an subclass of sanic_motor.BaseModel.'
                )
        super(DomainResource.__class__, cls).__init__(name, bases, clsdict)


class MongoDomainResource(DomainResource, metaclass=CheckMongoBackendMetaclass):
    @classmethod
    async def find(cls, query, **kwargs):
        return await cls.__backend__.find(**kwargs)

    @classmethod
    async def fetch(cls, _id=None, **kwargs):
        return await cls.__backend__.find_one(_id=_id, **kwargs)

    @classmethod
    async def query(cls, query):
        return await cls.__backend__.find(query.match)

    @classmethod
    async def remove_one(cls, item):
        return await cls.__backend__.remove_one(dict(_id=item._id))

    @classmethod
    async def update_one(cls, item, **changes):
        return await cls.__backend__.update_one(dict(_id=item._id), {'$set': changes})

    @classmethod
    async def insert_one(cls, item):
        return await cls.__backend__.insert_one(item.to_python())


class TestValidMongoDomainResource(MongoDomainResource):
    class __backend__(BaseModel):
        __coll__ = 'test-cqrs-resource'


try:
    class TestInvalidMongoDomainResource(MongoDomainResource):
        __backend__ = 'something ...'
except InvalidResourceBackend:
    pass
else:
    raise ValueError('Invalid __backend__ is not caught. [E21301]')
