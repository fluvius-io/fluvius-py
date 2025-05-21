from fluvius.domain.aggregate import action, Aggregate
from fluvius.data import serialize_mapping


class UserAggregate(Aggregate):
    @action("user-created", resources="user")
    async def create_user(self, stm, /, data):
        record = self.init_resource("user", data)
        await stm.insert(record)
        return {"_id": record._id}

    @action("user-updated", resources="user")
    async def update_user(self, stm, /, data):
        item = self.rootobj
        await stm.update(item, serialize_mapping(data))
        return item

    @action("user-invalidated", resources="user")
    async def invalidate_user(self, stm, /, data):
        item = self.rootobj
        await stm.invalidate(item)
        return item

