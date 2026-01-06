from fluvius.worker import FluviusWorker, export_task, export_cron
from fluvius.worker import SQLWorkTracker


class MyWorker(FluviusWorker):
    __queue_name__ = "my_queue"
    __tracker__ = SQLWorkTracker

    @export_cron(second=set(range(1, 59, 1)))
    async def my_cron(self, ctx):
        raise RuntimeError("A00.500", "Test error Something went wrong")

    @export_task
    async def my_task(self, ctx):
        raise RuntimeError("A00.500", "Test error Something went wrong")

worker = MyWorker()
worker.run()