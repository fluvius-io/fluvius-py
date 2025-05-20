from fluvius.domain import identifier
from . import domain as dmn, logger, context
import asyncio


async def main():
    ctx = context.SanicContext.create(
        namespace='app-user'
    )

    FIXTURE_ID = identifier.UUID_GENF(100)

    domain = dmn.UserDomain(ctx, )
    domain.set_aggroot('app-user', FIXTURE_ID)
    commands = [
        domain.create_command('activate-user'),
        domain.create_command('reconcile-user'),
        domain.create_command('deactivate-user'),
    ]
    async for resp in domain.command_processor.process(*commands):
        logger.info('Resp: %s', resp)


asyncio.run(main())
