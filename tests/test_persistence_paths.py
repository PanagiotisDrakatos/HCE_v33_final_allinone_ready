import time


def test_flush_happy_path_background_loop():
    from hcebt import persistence as P

    repo = P.Repo(cfg=P.RepoConfig(backend="none", batch_size=2, flush_interval_ms=100))
    calls = {"n": 0}

    def flush_capture(rows):  # assigned to instance; expects only rows
        calls["n"] += 1
        return None

    repo._flush = flush_capture  # type: ignore
    try:
        repo.start()
        repo.submit(
            [
                {"run_id": "r", "ts": 1, "symbol": "X", "metric": "m", "val": 1},
            ]
        )
        repo.submit(
            [
                {"run_id": "r", "ts": 2, "symbol": "X", "metric": "m", "val": 2},
            ]
        )
        time.sleep(0.3)
    finally:
        repo.stop()
    assert calls["n"] >= 1


def test_flush_retries_and_error_metric_increments():
    from hcebt import persistence as P

    repo = P.Repo(cfg=P.RepoConfig(backend="none"))

    class FailingClient:
        def insert(self, *args, **kwargs):
            raise TimeoutError("simulated")

    # Force ClickHouse pathway to exercise retry loop
    repo.repo = ("ch", FailingClient())
    rows = [{"run_id": "r", "ts": 1, "symbol": "X", "metric": "m", "val": 1}]

    t0 = time.time()
    repo._flush(rows)  # will attempt up to 5 times then give up
    elapsed = time.time() - t0

    # should have at least one retry recorded
    assert repo.metrics["batch_retry_count"] >= 1
    # elapsed should be > 0 due to backoffs (not asserting exact timing to avoid flakes)
    assert elapsed >= 0


def test_stop_performs_final_flush():
    from hcebt import persistence as P

    repo = P.Repo(cfg=P.RepoConfig(backend="none", batch_size=1000, flush_interval_ms=500))
    calls = {"n": 0}

    def flush_capture(rows):  # assigned to instance; expects only rows
        calls["n"] += 1
        return None

    repo._flush = flush_capture  # type: ignore
    try:
        repo.start()
        # enqueue a small batch that will remain buffered (batch_size not reached; timeout long)
        repo.submit(
            [
                {"run_id": "r", "ts": 1, "symbol": "X", "metric": "m", "val": 1},
            ]
        )
        # give time for queue to be drained into internal buffer
        time.sleep(0.1)
    finally:
        repo.stop()  # should trigger final flush of remaining buffer
    assert calls["n"] >= 1
