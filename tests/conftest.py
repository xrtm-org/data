import pytest
from datetime import datetime, timezone
from xrtm.data.schemas.forecast import MetadataBase

@pytest.fixture
def snapshot_time():
    return datetime.now(timezone.utc)

@pytest.fixture
def minimal_metadata(snapshot_time):
    return MetadataBase(snapshot_time=snapshot_time)
