from .domain import Domain
from . import config, logger


class DomainManager(object):
    __domains__ = tuple()
    __blacklisted_commands__ = tuple()
    __whitelisted_commands__ = tuple()

    @classmethod
    def register_domain(cls, domain_cls, whitelist=None, blacklist=None):
        if domain_cls in cls.__domains__:
            raise RuntimeError(f'Domain already registered with domain manager: {domain_cls}')

        cls.__domains__ += (domain_cls,)
        # cls.__whitelist__[domain_cls] = whitelist or tuple()
        # cls.__blacklist__[domain_cls] = blacklist or tuple()

    def initialize_domains(self, app):
        if hasattr(self, '_domains'):
            raise ValueError(f'Domains manager initialized')

        def _validate():
            for domain_cls in self.__domains__:
                if not issubclass(domain_cls, Domain):
                    raise ValueError(f'Invalid CQRS Domain: {domain_cls}')

                logger.info(f"Initializing domain: {domain_cls}")
                yield domain_cls(app)

        self._domains = tuple(_validate())
        return self._domains

    def _enumerate_command_handlers(self, domain):
        for cmd_key, cmd_cls, qual_name in domain.enumerate_command():
            if self.__blacklisted_commands__ and qual_name in self.__blacklisted_commands__:
                continue

            if self.__whitelisted_commands__ and qual_name not in self.__whitelisted_commands__:
                continue

            yield domain, qual_name, cmd_key, cmd_cls


    def enumerate_commands(self):
        for domain in self._domains:
            yield from self._enumerate_command_handlers(domain)

