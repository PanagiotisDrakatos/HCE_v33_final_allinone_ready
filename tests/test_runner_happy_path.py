import json
from pathlib import Path

def test_runner_run_ab_minimal(tmp_path: Path):
    from hcebt.runner import run_ab
    from hcebt.config import RunConfig

    # minimal deterministic event stream for A/B
    events = [
        {"ts":"2024-01-01T00:00:00Z","symbol":"X","bid":100.0,"ask":100.2,"last":100.1},
        {"ts":"2024-01-01T00:00:01Z","symbol":"X","bid":100.0,"ask":100.2,"last":100.1},
    ]

    cfg = RunConfig(run_id="test-run")
    res = run_ab(cfg, events, events)

    assert "A" in res and "B" in res and "repo_metrics" in res
    assert res["A"]["events"] == 2 and res["B"]["events"] == 2
    assert "fills" in res["A"] and "fills" in res["B"]

