import asyncio
import account_transaction.domain as dmn
import account_transaction.context as context
from account_transaction.cfg import logger
from account_transaction.resource import BankAccountResource
from account_transaction.fixture import ACCOUNT_ONE_ID, ACCOUNT_TWO_ID


async def print_account_data(domain, *ids):
    for id in ids:
        account_data = await domain.statemgr.fetch(
            resource="bank-account", _id=id
        )
        logger.info(account_data)


async def main():
    # account 1: 1000
    # account 2: 100
    BankAccountResource.init_fixture_data()

    ctx = context.SanicContext.create(
        namespace='bank-account'
    )

    domain = dmn.TransactionManagerDomain(ctx)
    domain.set_aggroot('bank-account', ACCOUNT_ONE_ID)

    logger.info("===== Before =====")
    await print_account_data(domain, ACCOUNT_ONE_ID, ACCOUNT_TWO_ID)

    commands = [
        domain.create_command('withdraw-money', data={"amount": 20}),
        domain.create_command('deposit-money', data={"amount": 10}),
        domain.create_command(
            'transfer-money',
            data={
                "amount": 30,
                "recipient": ACCOUNT_TWO_ID
            }
        )
    ]

    resps = await domain.process_command(*commands)

    for resp in resps:
        logger.info('Resp: %s', resp)

    logger.info("===== After =====")
    await print_account_data(domain, ACCOUNT_ONE_ID, ACCOUNT_TWO_ID)


asyncio.run(main())
