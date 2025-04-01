from datetime import datetime
from fluvius.data.serializer import deserialize_json

# @TODO: Need refactor


async def generate_cmd_from_pending_update(domain, batch_id, user):
    from fluvius.domain.backend.gino import PendingUpdateStore

    pending_commands = await PendingUpdateStore.fetch_pending_command(batch_id)
    errors = []
    cmds = ()
    raise_error = False
    for index, pending_command in enumerate(pending_commands):
        try:
            payload = pending_command.data
            if not isinstance(pending_command.data, dict):
                payload = deserialize_json(pending_command.data)

            domain.set_aggroot(
                resource=pending_command.aggroot__resource,
                identifier=pending_command.aggroot__identifier
            )
            cmd_key = pending_command._domain
            cmds += (domain.create_command(cmd_key, payload), )

        except Exception as e:
            raise_error = True
            errors.append({"index": (index + 1), "content": str(e)})

    if raise_error:
        raise ValueError(errors)

    return cmds


async def pending_command_ingress(domain, batch_id, user, payload):
    from fluvius.domain.backend.gino import PendingUpdateStore

    payload.update(dict(
        commit_time=datetime.utcnow(),
        committer=user._id
    ))
    batch_rs = []
    same_context = False
    try:
        async with domain.transaction_manager():
            for cmd in await generate_cmd_from_pending_update(domain, batch_id, user):
                domain.set_aggroot(resource=cmd.aggroot.resource, identifier=cmd.aggroot.identifier)
                if not same_context:
                    await domain.process_command(cmd)
                    same_context = True
                else:
                    await domain.process_command_with_existing_context(cmd)

                batch_rs.append(await domain.commit())

        await PendingUpdateStore.update_pending_update(batch_id, {"status": "COMMITTED", **payload})
        return batch_rs
    except Exception as e:
        await PendingUpdateStore.update_pending_update(batch_id, {"status": "ERROR", **payload})
        raise e
