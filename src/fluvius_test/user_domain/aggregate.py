from fluvius.domain.aggregate import action, Aggregate
from fluvius.data import serialize_mapping


class UserAggregate(Aggregate):
    @action("user-created", resources="user")
    async def create_user(self, data):
        record = self.init_resource("user", **serialize_mapping(data), _id=self.aggroot.identifier)
        await self.statemgr.insert(record)
        return {"_id": record._id}


    @action("user-updated", resources="user")
    async def update_user(self, data):
        item = self.rootobj
        await self.statemgr.update(item, **serialize_mapping(data))
        return item


    @action("user-invalidated", resources="user")
    async def invalidate_user(self):
        item = self.rootobj
        await self.statemgr.invalidate(item)
        return item

