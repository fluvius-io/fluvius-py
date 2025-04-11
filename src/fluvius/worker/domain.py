from fluvius.domain.context import DomainTransport

from .datadef import DomainWorkerRequest, DomainWorkerCommand
from .client import WorkerClient

from . import FluviusWorker, logger, export_cron, export_task


DEBUG = True


class DomainWorker(FluviusWorker):
    __domains__ = tuple()
    __whitelisted_commands__ = None
    __blacklisted_commands__ = None

    def __init__(self, *args, **kwargs):
        self._pre_init()
        super().__init__(*args, **kwargs)
        self._post_init()

    def _pre_init(self):
        self._domains = self._initialize_domains(self.__domains__)
        if not self._domains:
            raise ValueError(f'No domains registered for worker: {cls}')

        for domain in self._domains:
            self._functions += tuple(self._register_domain_handlers(domain))

    def _post_init(self):
        self._domain_ctx = {
            domain.domain_name: domain.setup_context(
                transport=DomainTransport.REDIS,
            ) for domain in self._domains
        }

    def _initialize_domains(self, domains):
        from fluvius.domain import Domain

        def _validate():
            for domain_cls in domains:
                if not issubclass(domain_cls, Domain):
                    raise ValueError(f'Invalid CQRS Domain: {domain_cls}')

                yield domain_cls(self)

        return tuple(_validate())

    def setup_context(self, domain, worker_ctx, **kwargs):
        return domain.setup_context(**kwargs)

    def _wrap_command(self, domain, cmd_key, qual_name):
        @export_task(name=qual_name)
        async def _handle_request(ctx, request: DomainWorkerRequest):
            context = self.setup_context(
                domain,
                ctx,
                headers=request.headers,
                transport=DomainTransport.REDIS,
                source=request.context.source
            )

            cmddata = request.command
            assert cmddata.command == cmd_key

            command = domain.create_command(
                cmd_key,
                cmddata.resource,
                cmddata.identifier,
                cmddata.payload,
                cmddata.domain_sid,
                cmddata.domain_iid
            )

            return await domain.handle_request(context, command)

        return _handle_request

    @export_task
    async def process_commands(ctx, *commands, headers=None):
        domain = self._domains[0]
        context = self.setup_context(
            domain,
            ctx,
            headers=headers,
            transport=DomainTransport.REDIS
        )
        cmds = [
            domain.create_command(
                cmddata.command,
                cmddata.resource,
                cmddata.identifier,
                cmddata.payload,
                cmddata.domain_sid,
                cmddata.domain_iid
            )
            for cmddata in commands
        ]
        return await domain.handle_request(context, *cmds)

    def _register_domain_handlers(self, domain):
        for cmd_key, cmd_cls, qual_name in domain.enumerate_command():
            if self.__blacklisted_commands__ and qual_name in self.__blacklisted_commands__:
                continue

            if self.__whitelisted_commands__ and qual_name not in self.__whitelisted_commands__:
                continue

            yield self._wrap_command(domain, cmd_key, qual_name)


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


