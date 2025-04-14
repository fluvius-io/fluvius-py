from fluvius.tracker import SQLTracker
import pytest

class SampleSQLTracker(SQLTracker):
    pass

@pytest.mark.asyncio
async def test_tracker():
    tracker = SampleSQLTracker()
    tracker.connect()
    print(await tracker.add_entry('arq-worker', hostname="test"))
