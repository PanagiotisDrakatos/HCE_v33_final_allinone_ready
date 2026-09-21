"""`backtest.py run` exits non-zero when a batch was lost, so a silent write
failure can no longer read as success."""

import json

import backtest
from click.testing import CliRunner


def _cfg(tmp_path):
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text("run_id: t\nstrat_id: s\nbatch:\n  backend: none\n")
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    a.write_text("[]")
    b.write_text("[]")
    return str(cfg), str(a), str(b)


def _invoke(monkeypatch, tmp_path, metrics):
    def fake_run_ab(_cfg, _a, _b):
        return {"A": {}, "B": {}, "repo_metrics": metrics}

    monkeypatch.setattr(backtest, "run_ab", fake_run_ab)
    cfg, a, b = _cfg(tmp_path)
    return CliRunner().invoke(backtest.cli, ["run", "--config", cfg, "--ab", a, b])


def test_exit_2_on_failed_batches(monkeypatch, tmp_path):
    r = _invoke(
        monkeypatch, tmp_path, {"failed_batches": 1, "dropped_batches": 0, "unflushed": False}
    )
    assert r.exit_code == 2


def test_exit_2_on_dropped_batches(monkeypatch, tmp_path):
    r = _invoke(
        monkeypatch, tmp_path, {"failed_batches": 0, "dropped_batches": 3, "unflushed": False}
    )
    assert r.exit_code == 2


def test_exit_2_on_unflushed(monkeypatch, tmp_path):
    r = _invoke(
        monkeypatch, tmp_path, {"failed_batches": 0, "dropped_batches": 0, "unflushed": True}
    )
    assert r.exit_code == 2


def test_exit_0_when_clean(monkeypatch, tmp_path):
    r = _invoke(
        monkeypatch, tmp_path, {"failed_batches": 0, "dropped_batches": 0, "unflushed": False}
    )
    assert r.exit_code == 0
    assert json.loads(r.output)["repo_metrics"]["failed_batches"] == 0
