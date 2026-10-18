import time
from truth_mirror.pipeline_status import cleanup_stale, set_stage, _statuses, _EXPIRY_SECONDS

def test_expiry_and_throttling():
    assert _EXPIRY_SECONDS == 3600
    _statuses.clear()
    set_stage("test_stage", "req_1")
    _statuses["req_1"]["updated_at"] = time.time() - 4000
    # Simulate immediate cleanup call to test throttle
    removed = cleanup_stale()
    # It should not remove it yet due to throttle lock if called repeatedly
    assert removed == 0
    assert "req_1" in _statuses
