from fluvius.domain import logger
from fluvius.domain.aggregate import action, Aggregate, ALL_RESOURCES


class ObjectAggregate(Aggregate):
    @action('object-updated', resource='people-economist')
    async def update(self, stm, person, / , content):
        await stm.update_one('people-economist', person._id, content, etag=person._etag)
        return {'_id': person._id}

    @action('object-replaced', resource='people-economist')
    async def replace(self, stm, person, / , content):
        if "_id" in content and content["_id"] != person["_id"]:
            raise ValueError("Object replacement must not change existing _id")

        await stm.update_one('people-economist', person._id, content, etag=person._etag)
        return {'_id': person._id}

    @action('object-created')
    async def create(self, stm, / , content):
        person = self.init_resource(content)
        await stm.insert_one('people-economist', person)
        return {'_id': person._id}

    @action('object-removed', resource=ALL_RESOURCES)
    async def remove(self, stm, obj):
        await stm.invalidate_one('people-economist', obj._id)
        return {'_id': obj._id}

    @action('action-logged')
    async def log(self, stm, / , cmd):
        logger.info("[LOG COMMAND HANDLER]: %.100s...", cmd)
        return {}

    @action('action-logged')
    async def log_tested(self, stm, / , cmd):
        logger.info("[LOG COMMAND HANDLER]: %.100s...", cmd)
        return {}
