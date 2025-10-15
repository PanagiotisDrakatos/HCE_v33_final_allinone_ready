import time
import pytest

def test_queue_full_metric_exposed():
    from hcebt import persistence as P
    repo = P.Repo(cfg=P.RepoConfig(backend="none", batch_size=1000, flush_interval_ms=100, queue_max=1))
    try:
        for i in range(10):
            repo.submit([{"run_id":"r","ts":i,"symbol":"X","metric":"m","val":i}])
        time.sleep(0.3)
    finally:
        repo.stop()
    assert repo.metrics.get("submitted_batches", 0) >= 1
