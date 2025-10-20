from hatchet_sdk import Hatchet

from .helper import build_hatchet_config
from ._meta import config, logger


class HatchetClient(object):
    __hatchet_config__ = None

    def __init__(self, **kwargs):
        if self.__hatchet_config__ is None:
            raise ValueError("Hatchet config is not set")

        self.__hatchet__ = Hatchet(config=build_hatchet_config(self.__hatchet_config__))
    
    async def send(self, workflow_name, *args, **kwargs):
        workflow = self.__hatchet__.workflow(name=workflow_name)
        logger.debug(f"Sending workflow {workflow_name} with args {args} and kwargs {kwargs}")
        return await workflow.aio_run_no_wait(*args, **kwargs)
    
    async def request(self, workflow_name, *args, **kwargs):
        logger.debug(f"Requesting workflow {workflow_name} with args {args} and kwargs {kwargs}")
        response = await self.send(workflow_name, *args, **kwargs)
        result = response.result()
        logger.debug(f"Result: {result}")
        return result
    