"""cmd_runtime with an injected subprocess seam (no Docker). Proves the read-back
gate, health gate, teardown-on-failure, exclusive lock, tool-missing handling,
and per-call unique project names."""

import json
import types

import verify


class Done:
    def __init__(self, rc=0, out="", err=""):
        self.returncode, self.stdout, self.stderr = rc, out, err


def make_run(
    readback="4|2",
    regclass="market_signals",
    up_rc=0,
    health='{"Name":"timescaledb","Health":"healthy"}',
    raise_on=None,
):
    calls = []

    def run(cmd, **kw):
        calls.append(list(cmd))
        joined = " ".join(cmd)
        if raise_on and raise_on in joined:
            raise FileNotFoundError(raise_on)
        if "status" in cmd and "--porcelain" in cmd:
            return Done(out="")  # clean tree
        if "rev-parse" in cmd:
            return Done(out="t" * 40)
        if "up" in cmd and "-d" in cmd:
            return Done(rc=up_rc)
        if "ps" in cmd:
            return Done(out=health)
        if "port" in cmd:
            return Done(out="127.0.0.1:49153")
        if "to_regclass" in joined:
            return Done(out=regclass)
        if "count(" in joined:
            return Done(out=readback)
        return Done()

    run.calls = calls
    return run


def _args(root, **over):
    ns = types.SimpleNamespace(root=str(root), project="")
    ns.__dict__.update(over)
    return ns


def _down_called(run):
    return any("down" in c and "-v" in c for c in run.calls)


def test_happy_path_passes_and_tears_down(tmp_path):
    run = make_run(readback="4|2")
    rc = verify.cmd_runtime(_args(tmp_path), run=run)
    assert rc == 0
    assert _down_called(run)
    state = json.loads((tmp_path / ".verify/state.json").read_text())
    assert "timescale-roundtrip" in state["features_verified"]


def test_zero_rows_is_fail_and_tears_down(tmp_path):
    run = make_run(readback="0|0")
    rc = verify.cmd_runtime(_args(tmp_path), run=run)
    assert rc == 1
    assert _down_called(run)
    state = json.loads((tmp_path / ".verify/state.json").read_text())
    assert "timescale-roundtrip" not in state["features_verified"]


def test_missing_table_is_inconclusive(tmp_path):
    run = make_run(regclass="")
    rc = verify.cmd_runtime(_args(tmp_path), run=run)
    assert rc == 1
    state = json.loads((tmp_path / ".verify/state.json").read_text())
    rt = [c for c in state["checks"] if c["id"] == "runtime-timescale"][0]
    assert rt["status"] == "INCONCLUSIVE"


def test_unhealthy_is_not_pass(tmp_path):
    run = make_run(health='{"Name":"timescaledb","Health":""}')
    rc = verify.cmd_runtime(_args(tmp_path), run=run)
    assert rc == 1


def test_up_failure_is_fail(tmp_path):
    run = make_run(up_rc=1)
    rc = verify.cmd_runtime(_args(tmp_path), run=run)
    assert rc == 1
    state = json.loads((tmp_path / ".verify/state.json").read_text())
    rt = [c for c in state["checks"] if c["id"] == "runtime-timescale"][0]
    assert rt["status"] == "FAIL"


def test_lock_is_exclusive(tmp_path):
    (tmp_path / ".verify").mkdir()
    (tmp_path / ".verify/lock").write_text("held")
    run = make_run()
    rc = verify.cmd_runtime(_args(tmp_path), run=run)
    assert rc == 1
    assert not any("up" in c for c in run.calls)  # never started


def test_tool_missing_is_inconclusive(tmp_path):
    run = make_run(raise_on="pull")
    rc = verify.cmd_runtime(_args(tmp_path), run=run)
    assert rc == 1
    state = json.loads((tmp_path / ".verify/state.json").read_text())
    rt = [c for c in state["checks"] if c["id"] == "runtime-timescale"][0]
    assert rt["status"] == "INCONCLUSIVE"


def test_project_name_unique_per_call(tmp_path):
    seen = set()
    for _ in range(2):
        run = make_run()
        verify.cmd_runtime(_args(tmp_path), run=run)
        (tmp_path / ".verify/lock").unlink(missing_ok=True)
        proj = next(c[c.index("-p") + 1] for c in run.calls if "-p" in c)
        assert proj.startswith("hce-verify-")
        seen.add(proj)
    assert len(seen) == 2
