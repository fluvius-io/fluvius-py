from fluvius.domain.manager import DomainManager
from fluvius.domain.context import DomainTransport

from .datadef import DomainWorkerRequest, DomainWorkerCommand
from .client import WorkerClient

from . import FluviusWorker, logger, config, export_cron, export_task


DEBUG = config.DEBUG


class DomainWorker(FluviusWorker, DomainManager):
    def __init__(self, *args, **kwargs):
        self._register_domain_functions()
        super().__init__(*args, **kwargs)

    def _register_domain_functions(self):
        self.initialize_domains(self)
        self._functions += tuple(
            self._generate_handler(*params)
            for params in self.enumerate_commands()
        )

    def _generate_handler(self, domain, qual_name, cmd_key, cmd_cls):
        @export_task(name=qual_name)
        async def _handle_request(ctx, request: DomainWorkerRequest):
            context = domain.setup_context(
                headers=request.headers,
                transport=DomainTransport.REDIS,
                source=request.context.source
            )

            cmddata = request.command
            command = domain.create_command(
                cmd_key,
                cmddata.payload,
                aggroot=(
                    cmddata.resource,
                    cmddata.identifier,
                    cmddata.domain_sid,
                    cmddata.domain_iid
                )
            )

            return await domain.process_command(command, context=context)

        return _handle_request


class DomainWorkerClient(WorkerClient):
    async def send(self, entrypoint, _relation=None, _context=None, _headers=None, **kwargs):
        command = DomainWorkerCommand(**kwargs)
        request = DomainWorkerRequest(
            command=command,
            context=_context,
            relation=_relation,
            headers=_headers,
        )
        return await self.enqueue_job(entrypoint, request, _queue_name=self.queue_name)

    async def request(self, *args, **kwargs):
        handle = await self.send(*args, **kwargs)
        result = await handle.result()
        DEBUG and logger.info("[ARQ] Command Result [%s]: %s", *args, result)
        return result


