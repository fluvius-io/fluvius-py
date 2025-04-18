from .domain import Domain
from . import config, logger


class DomainManager(object):
    __domains__ = tuple()
    __whitelist__ = dict()
    __blacklist__ = dict()
    __blacklisted_commands__ = tuple()
    __whitelisted_commands__ = tuple()

    @classmethod
    def register_domain(cls, domain_cls, whitelist=None, blacklist=None):
        if domain_cls in cls.__domains__:
            raise RuntimeError(f'Domain already registered with domain manager: {domain_cls}')

        cls.__domains__ += (domain_cls,)
        cls.__whitelist__[domain_cls] = whitelist or tuple()
        cls.__blacklist__[domain_cls] = blacklist or tuple()

    def __init__(self, app, *args, **kwargs):
        self._init_domain_manager(app)

    def _init_domain_manager(self, app):
        self._domains = self._initialize_domains(app, self.__domains__)
        if not self._domains:
            raise ValueError(f'No domains registered {cls}')

    def _initialize_domains(self, app, domains):
        def _validate():
            for domain_cls in domains:
                if not issubclass(domain_cls, Domain):
                    raise ValueError(f'Invalid CQRS Domain: {domain_cls}')

                logger.info(f"Initializing domain: {domain_cls}")
                yield domain_cls(app)

        return tuple(_validate())

    def _wrap_command(self, domain, cmd_key, qual_name):
        async def _command_handler(domain_ctx, command_payload, command_aggroot):
            command = domain.create_command(
                cmd_key,
                command_payload,
                command_aggroot
            )

            return await domain.process_command(domain_ctx, command)
        _command_handler.__name__ = f"{cmd_key}_handler"
        return _command_handler

    def _enumerate_command_handlers(self, domain):
        for cmd_key, cmd_cls, qual_name in domain.enumerate_command():
            if self.__blacklisted_commands__ and qual_name in self.__blacklisted_commands__:
                continue

            if self.__whitelisted_commands__ and qual_name not in self.__whitelisted_commands__:
                continue

            yield domain.__domain__, cmd_key, self._wrap_command(domain, cmd_key, qual_name)

    def enumerate_command_handlers(self):
        for domain in self._domains:
            yield from self._enumerate_command_handlers(domain)

