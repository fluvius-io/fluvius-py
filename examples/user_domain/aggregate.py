from fluvius.domain.aggregate import action, Aggregate


class UserAggregate(Aggregate):
    @action('user-created')
    async def create(self, stm, / , content):
        user = self.init_resource(content)
        await stm.insert_one('user', user)
        return {'_id': user._id}
