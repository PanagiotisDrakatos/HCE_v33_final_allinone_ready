from __future__ import annotations

from hcebt.persistence import Repo, RepoConfig


class _FakeCursor:
    def __init__(self):
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, args):
        self.executed.append((sql, list(args)))


class _FakeTSConn:
    def __init__(self):
        self.autocommit = False
        self.cur = _FakeCursor()
        self.closed = False

    def cursor(self):
        return self.cur

    def close(self):
        self.closed = True


class _FakeCHClient:
    def __init__(self):
        self.calls = []

    def insert(self, table, data, column_names=None):
        self.calls.append((table, data, list(column_names or [])))


def _rows_with_dupes():
    base = {
        "run_id": "r1",
        "ts": 1,
        "symbol": "BTC",
        "metric": "m",
        "value": 42,
    }
    # duplicate PK row with different value should be deduped by _flush
    return [base, {**base, "value": 43}]


def test_flush_timescale_builds_upsert_sql_and_args():
    repo = Repo(RepoConfig())  # backend none
    ts = _FakeTSConn()
    repo.repo = ("ts", ts)

    repo._flush(_rows_with_dupes())

    assert len(ts.cur.executed) == 1
    sql, args = ts.cur.executed[0]
    # Expected upsert with ON CONFLICT on PK
    assert "ON CONFLICT (run_id,ts,symbol,metric) DO UPDATE SET" in sql
    # args contain one set per unique row; after dedupe, only one row remains
    # Columns are sorted; expect at least PK + value column
    assert len(args) >= 5


def test_flush_clickhouse_inserts_with_sorted_columns():
    repo = Repo(RepoConfig())
    ch = _FakeCHClient()
    repo.repo = ("ch", ch)

    repo._flush(_rows_with_dupes())

    assert len(ch.calls) == 1
    table, data, cols = ch.calls[0]
    assert isinstance(data, list) and len(data) == 1  # deduped to one row
    assert cols == sorted(cols) and set(cols) >= {"run_id", "ts", "symbol", "metric", "value"}


def test_submit_drops_when_queue_full_and_metrics_updated():
    cfg = RepoConfig(queue_max=1)
    repo = Repo(cfg)
    # First batch enqueued
    repo.submit([{"run_id": "a", "ts": 1, "symbol": "X", "metric": "m"}])
    # This should drop due to full queue
    repo.submit([{"run_id": "b", "ts": 1, "symbol": "Y", "metric": "m"}])
    assert repo.metrics["submitted_batches"] == 1
    assert repo.metrics["dropped_batches"] == 1


def test_stop_closes_timescale_connection():
    repo = Repo(RepoConfig())
    ts = _FakeTSConn()
    repo.repo = ("ts", ts)
    repo.stop()
    assert ts.closed is True


def test_repo_config_queue_max_batches_backcompat():
    cfg = RepoConfig(queue_max=10, queue_max_batches=5)
    assert cfg.queue_max == 5
    assert cfg.queue_max_batches_prop == 5
