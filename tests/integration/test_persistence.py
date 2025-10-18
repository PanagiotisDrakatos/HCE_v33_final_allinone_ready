import os
import time
import uuid

import pytest

from hcebt.persistence import Repo, RepoConfig


@pytest.mark.skipif(not os.getenv("IT_CLICKHOUSE"), reason="ClickHouse IT disabled")
def test_clickhouse_write_smoke():
    repo = Repo(
        RepoConfig(
            backend="clickhouse",
            clickhouse_url=os.getenv("CLICKHOUSE_URL", "http://localhost:8123"),
            table="hce.market_signals",
        )
    )
    repo.start()
    rid = "it-" + str(uuid.uuid4())
    repo.submit(
        [
            {
                "run_id": rid,
                "ts": "2024-01-01T00:00:00+00:00",
                "symbol": "BTCUSDT",
                "metric": "fill_cost",
                "value": 1.23,
                "label": "A",
            }
        ]
    )
    time.sleep(1.0)
    repo.stop()


@pytest.mark.skipif(not os.getenv("IT_TIMESCALE"), reason="Timescale IT disabled")
def test_timescale_write_smoke():
    repo = Repo(
        RepoConfig(
            backend="timescale",
            timescale_dsn=os.getenv(
                "TIMESCALE_DSN",
                "postgresql://postgres:postgres@localhost:5432/hce",
            ),
            table="market_signals",
        )
    )
    repo.start()
    rid = "it-" + str(uuid.uuid4())
    repo.submit(
        [
            {
                "run_id": rid,
                "ts": "2024-01-01T00:00:00+00:00",
                "symbol": "BTCUSDT",
                "metric": "fill_cost",
                "value": 2.34,
                "label": "B",
            }
        ]
    )
    time.sleep(1.0)
    repo.stop()
