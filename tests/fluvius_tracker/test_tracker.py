from fluvius.tracker import SQLTracker
import pytest

class SampleSQLTracker(SQLTracker, trackers=('worker', 'worker-job', 'job-relation')):
    pass

@pytest.mark.asyncio
async def test_tracker():
    tracker = SampleSQLTracker()
    print(await tracker.add_entry('worker', hostname="test"))
