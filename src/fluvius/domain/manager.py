from fluvius.helper import load_class

from .domain import Domain
from . import config, logger


class DomainManager(object):
    __domains__ = tuple()
    __blacklisted_commands__ = tuple()
    __whitelisted_commands__ = tuple()

    def register_domain(self, *domain_classes, whitelist=tuple(), blacklist=tuple()):
        for domain_spec in domain_classes:
            domain_cls = load_class(domain_spec, base_class=Domain)
            if domain_spec in self.__domains__:
                raise RuntimeError(f'Domain already registered with domain manager: {domain_spec}')

            self.__domains__ += (domain_cls,)

        self.__blacklisted_commands__ += blacklist
        self.__whitelisted_commands__ += whitelist


    def initialize_domains(self, app):
        if hasattr(self, '_domains'):
            raise RuntimeError(f'Domains manager already initialized.')

        def _validate():
            for domain_cls in self.__domains__:
                logger.info(f"Initializing domain: {domain_cls}")
                yield domain_cls(app)

        self._domains = tuple(_validate())
        return self._domains

    def _enumerate_command_handlers(self, domain):
        for cmd_cls, cmd_key, fq_name in domain.enumerate_command():
            # Never list blacklisted commands
            if fq_name in self.__blacklisted_commands__:
                continue

            if (not self.__whitelisted_commands__ or       # If no whitelist presence, enumerate all
                fq_name in self.__whitelisted_commands__): # Always list whitelisted commands, except they are blacklisted
                yield domain, cmd_cls, cmd_key, fq_name


    def enumerate_commands(self):
        for domain in self._domains:
            yield from self._enumerate_command_handlers(domain)

