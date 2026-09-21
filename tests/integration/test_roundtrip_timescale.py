import os
import uuid

import pytest

from hcebt.persistence import Repo, RepoConfig

pytestmark = [pytest.mark.integration]

DSN = os.environ.get("TIMESCALE_DSN", "postgresql://postgres:postgres@localhost:5432/hce")


@pytest.mark.skipif(os.environ.get("IT_TIMESCALE") != "1", reason="set IT_TIMESCALE=1 to enable")
def test_roundtrip_timescale():
    """Write two rows through the real writer, then read them back with an
    independent connection. Proves persistence, not just connection."""
    import psycopg

    run_id = "rt-" + uuid.uuid4().hex[:8]
    repo = Repo(
        RepoConfig(backend="timescale", timescale_dsn=DSN, batch_size=1, table="market_signals")
    )
    repo.start()
    for i, label in enumerate(("A", "B")):
        repo.submit(
            [
                {
                    "run_id": run_id,
                    "ts": f"2024-01-01T00:00:0{i}+00:00",
                    "symbol": "BTCUSDT",
                    "metric": "fill_cost",
                    "value": float(i),
                    "label": label,
                }
            ]
        )
    repo.stop()
    assert repo.metrics["failed_batches"] == 0
    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT count(*), count(DISTINCT label) FROM market_signals WHERE run_id=%s",
            (run_id,),
        )
        rows, labels = cur.fetchone()
    assert (rows, labels) == (2, 2)
