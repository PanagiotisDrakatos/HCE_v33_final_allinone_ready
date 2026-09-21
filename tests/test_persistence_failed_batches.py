"""The write path must surface a lost batch. A write that fails after its retry
budget increments failed_batches, and stop() must not return before that count
is settled (the join-until-exit fix)."""

import time

from hcebt.persistence import Repo, RepoConfig


def test_write_failure_counts_failed_batches(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda *_a, **_k: None)  # no backoff wait
    repo = Repo(RepoConfig(backend="none", batch_size=1, flush_interval_ms=10))

    def boom(_rows):
        raise RuntimeError("db down")

    monkeypatch.setattr(repo, "_write_rows", boom)
    repo.start()
    repo.submit(
        [
            {
                "run_id": "r",
                "ts": "2024-01-01T00:00:00+00:00",
                "symbol": "BTCUSDT",
                "metric": "fill_cost",
                "value": 1.0,
                "label": "A",
            }
        ]
    )
    repo.stop()
    assert repo.metrics["failed_batches"] >= 1
    assert repo.metrics["unflushed"] is False  # loop exited before stop() returned


def test_clean_run_has_zero_failed_and_not_unflushed():
    repo = Repo(RepoConfig(backend="none", batch_size=1, flush_interval_ms=10))
    repo.start()
    repo.submit(
        [
            {
                "run_id": "r",
                "ts": "2024-01-01T00:00:00+00:00",
                "symbol": "BTCUSDT",
                "metric": "fill_cost",
                "value": 1.0,
                "label": "A",
            }
        ]
    )
    repo.stop()
    assert repo.metrics["failed_batches"] == 0
    assert repo.metrics["unflushed"] is False
    assert repo.metrics["dropped_batches"] == 0
