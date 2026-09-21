#!/usr/bin/env python3
"""Deterministic verification kernel for the HCE backtest engine.

One entry point for humans, the pre-push hook, and CI. Produces a
content-addressed evidence receipt bound to the source tree, proves one real
runtime feature (Timescale write then read-back), and refuses a stale or
forged receipt. Standard library only.

Subcommands: fast | runtime | security | receipt | check | clean
Pure helpers live in verify_core; this module holds the CLI and the handlers
that touch the filesystem, Docker, and the accumulated run state.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verify_core as core  # noqa: E402

STATE = ".verify/state.json"
RECEIPT = ".verify/receipt.json"
LOCK = ".verify/lock"


def _load_state(root="."):
    p = Path(root) / STATE
    if p.is_file():
        return json.loads(p.read_text())
    return {
        "checks": [],
        "container_health": [],
        "security": [],
        "features_verified": [],
        "runtime": {},
        "started_at": _now(),
    }


def _save_state(state, root="."):
    p = Path(root) / STATE
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2))


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _add_check(state, cid, status, exit_code=None, duration_ms=None, **extra):
    rec = {
        "id": cid,
        "status": status,
        "ok": status == "PASS",
        "exit_code": exit_code,
        "duration_ms": duration_ms,
    }
    rec.update(extra)
    state["checks"] = [c for c in state["checks"] if c.get("id") != cid]
    state["checks"].append(rec)
    return rec


def _free_lock(root):
    try:
        Path(root, LOCK).unlink()
    except FileNotFoundError:
        pass


def _read_pip_audit_ignores(root):
    """Dated, auditable pip-audit vuln ignore list. One id per line; text after
    '#' is a required rationale/review date. Applied identically here and in CI.
    """
    p = Path(root, "verification", "pip-audit-ignore.txt")
    if not p.is_file():
        return []
    ids = []
    for line in p.read_text().splitlines():
        vid = line.split("#", 1)[0].strip()
        if vid:
            ids.append(vid)
    return ids


def cmd_fast(args, run=subprocess.run):
    root = args.root
    state = _load_state(root)
    Path(root, ".verify").mkdir(parents=True, exist_ok=True)
    for cid, cmd in (
        ("ruff-format", ["ruff", "format", "--check", "."]),
        ("ruff-check", ["ruff", "check", "."]),
    ):
        t0 = time.monotonic()
        try:
            r = core.run_cmd(cmd, run=run, cwd=root)
            status, rc = ("PASS" if r.returncode == 0 else "FAIL"), r.returncode
        except FileNotFoundError:
            status, rc = "INCONCLUSIVE", None
        _add_check(state, cid, status, rc, int((time.monotonic() - t0) * 1000))
    junit = str(Path(root, ".verify", "unit.xml"))
    t0 = time.monotonic()
    try:
        # `python -m pytest` so the repo root is on sys.path and hcebt imports
        # without an editable install (keeps the tree clean for the receipt).
        r = core.run_cmd(
            [sys.executable, "-m", "pytest", "-m", "not integration", f"--junitxml={junit}"],
            run=run,
            cwd=root,
        )
        rc = r.returncode
    except FileNotFoundError:
        rc = None
    collected = skipped = 0
    status = "INCONCLUSIVE"
    if Path(junit).is_file():
        collected, skipped, status = core.parse_junit(Path(junit).read_text())
    _add_check(
        state,
        "pytest",
        status,
        rc,
        int((time.monotonic() - t0) * 1000),
        collected=collected,
        skipped=skipped,
    )
    _save_state(state, root)
    agg = core.result_of([c for c in state["checks"] if c["id"] in core.REQUIRED_CHECK_IDS])
    print(f"fast: {agg}")
    return 0 if agg == "PASS" else 1


def cmd_security(args, run=subprocess.run):
    root = args.root
    state = _load_state(root)
    findings = []
    t0 = time.monotonic()
    status = "INCONCLUSIVE"
    try:
        r = core.run_cmd(
            ["bandit", "-q", "-r", "hcebt", "lib", "backtest.py", "-lll", "-iii", "-f", "json"],
            run=run,
            cwd=root,
        )
        try:
            results = json.loads(r.stdout or "{}").get("results", [])
        except json.JSONDecodeError:
            results = []
        high = [
            x
            for x in results
            if x.get("issue_severity") == "HIGH" and x.get("issue_confidence") == "HIGH"
        ]
        findings += [
            {
                "tool": "bandit",
                **{
                    k: x.get(k)
                    for k in (
                        "test_id",
                        "issue_severity",
                        "issue_confidence",
                        "filename",
                        "line_number",
                    )
                },
            }
            for x in high
        ]
        status = "FAIL" if high else "PASS"
    except FileNotFoundError:
        status = "INCONCLUSIVE"
    _add_check(
        state,
        "bandit",
        status,
        None,
        int((time.monotonic() - t0) * 1000),
        high_findings=sum(1 for f in findings if f["tool"] == "bandit"),
    )
    t0 = time.monotonic()
    status = "INCONCLUSIVE"
    ignores = _read_pip_audit_ignores(root)
    try:
        cmd = ["pip-audit", "-r", "requirements.txt", "-r", "requirements-dev.txt", "-f", "json"]
        for vid in ignores:
            cmd += ["--ignore-vuln", vid]
        r = core.run_cmd(cmd, run=run, cwd=root)
        try:
            data = json.loads(r.stdout or "{}")
        except json.JSONDecodeError:
            data = {}
        deps = data.get("dependencies", data if isinstance(data, list) else [])
        fixable = [
            {
                "tool": "pip-audit",
                "id": v.get("id"),
                "name": dep.get("name"),
                "fix": v.get("fix_versions"),
            }
            for dep in deps
            for v in dep.get("vulns", [])
            if v.get("fix_versions") and v.get("id") not in ignores
        ]
        findings += fixable
        status = "FAIL" if fixable else "PASS"
    except FileNotFoundError:
        status = "INCONCLUSIVE"
    _add_check(
        state,
        "pip-audit",
        status,
        None,
        int((time.monotonic() - t0) * 1000),
        fixable_vulns=sum(1 for f in findings if f["tool"] == "pip-audit"),
    )
    state["security"] = findings
    _save_state(state, root)
    agg = core.result_of([c for c in state["checks"] if c["id"] in ("bandit", "pip-audit")])
    print(f"security: {agg}")
    return 0 if agg != "FAIL" else 1


def _write_cfg(root, run_id, port):
    cfg = Path(root, ".verify", f"cfg-{run_id}.yaml")
    dsn = f"postgresql://postgres:postgres@127.0.0.1:{port}/hce"
    cfg.write_text(
        f"run_id: {run_id}\nstrat_id: verify\n"
        f"fill:\n  slip_mode: bps\n  bps: 2.0\n  seed: 777\n"
        f"batch:\n  backend: timescale\n  batch_size: 1\n"
        f"  timescale_dsn: {dsn}\n  table: market_signals\n"
    )
    return str(cfg)


def _psql(compose, sql, run, root):
    return core.run_cmd(
        compose + ["exec", "-T", "timescaledb", "psql", "-U", "postgres", "-d", "hce", "-tAc", sql],
        run=run,
        cwd=root,
    )


def _backtest_proof(compose, run, root, state):
    """Drive the backtest against a healthy Timescale and read the rows back with
    an independent psql. Returns (status, rows, labels); appends the runtime
    feature to state only when the exact {A:2, B:2} distribution lands."""
    port = (
        core.run_cmd(compose + ["port", "timescaledb", "5432"], run=run, cwd=root)
        .stdout.strip()
        .rsplit(":", 1)[-1]
    )
    run_id = "verify-" + uuid.uuid4().hex[:8]
    cfg = _write_cfg(root, run_id, port)
    core.run_cmd(
        [
            sys.executable,
            "backtest.py",
            "run",
            "--config",
            cfg,
            "--ab",
            "verification/fixtures/A.json",
            "verification/fixtures/B.json",
        ],
        run=run,
        cwd=root,
    )
    if not _psql(compose, "SELECT to_regclass('market_signals')", run, root).stdout.strip():
        return "INCONCLUSIVE", None, None
    # Assert the exact per-label distribution, not just cardinality: a swapped
    # A/B would still give 4 rows and 2 labels, so group by label.
    rb = _psql(
        compose,
        f"SELECT label, count(*) FROM market_signals "
        f"WHERE run_id='{run_id}' GROUP BY label ORDER BY label",
        run,
        root,
    )
    counts = {}
    for line in rb.stdout.strip().splitlines():
        parts = line.replace(" ", "").split("|")
        if len(parts) == 2 and parts[1].isdigit():
            counts[parts[0]] = int(parts[1])
    rows, labels = sum(counts.values()), len(counts)
    if counts == core.TIMESCALE_EXPECTED:
        state["features_verified"] = sorted(
            set(state.get("features_verified", []) + [core.RUNTIME_FEATURE])
        )
        return "PASS", rows, labels
    return "FAIL", rows, labels


def cmd_runtime(args, run=subprocess.run):
    """Bring up Timescale, drive the backtest, read rows back independently."""
    root = args.root
    Path(root, ".verify").mkdir(parents=True, exist_ok=True)
    state = _load_state(root)
    tree, _, _ = core.git_tree_hash(root, run=run)
    project = args.project or f"hce-verify-{tree[:8]}-{uuid.uuid4().hex[:4]}"
    try:
        fd = os.open(str(Path(root, LOCK)), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, project.encode())
        os.close(fd)
    except FileExistsError:
        print("runtime: another verify holds .verify/lock", file=sys.stderr)
        return 1

    # A SIGTERM (CI cancellation, timeout, kill) must still run the teardown, so
    # turn it into a KeyboardInterrupt that the try/finally below catches.
    def _on_sigterm(_signum, _frame):
        raise KeyboardInterrupt("SIGTERM during runtime verify")

    prev_term = signal.getsignal(signal.SIGTERM)
    try:
        signal.signal(signal.SIGTERM, _on_sigterm)
    except (ValueError, OSError):
        prev_term = None  # not the main thread; rely on try/finally alone
    compose = [
        "docker",
        "compose",
        "-f",
        "docker-compose.yml",
        "-f",
        "compose.verify.yml",
        "-p",
        project,
    ]
    runtime = {"started": False, "healthy": False, "pull_ms": 0, "up_wait_ms": 0, "startup_ms": 0}
    status, rows, labels = "INCONCLUSIVE", None, None
    try:
        t0 = time.monotonic()
        try:
            core.run_cmd(compose + ["pull", "timescaledb"], run=run, cwd=root)
        except FileNotFoundError:
            print("runtime: docker compose plugin missing", file=sys.stderr)
            _add_check(state, core.RUNTIME_CHECK_ID, "INCONCLUSIVE", None, 0, reason="tool-missing")
            state["runtime"] = runtime
            _save_state(state, root)
            return 1
        runtime["pull_ms"] = int((time.monotonic() - t0) * 1000)
        t0 = time.monotonic()
        up = core.run_cmd(
            compose + ["up", "-d", "--wait", "--wait-timeout", "120", "timescaledb"],
            run=run,
            cwd=root,
        )
        runtime["up_wait_ms"] = int((time.monotonic() - t0) * 1000)
        runtime["started"] = True
        health = core.parse_compose_health(
            core.run_cmd(compose + ["ps", "--format", "json"], run=run, cwd=root).stdout
        )
        state["container_health"] = health
        runtime["healthy"] = bool(health) and all(h["status"] == "PASS" for h in health)
        runtime["startup_ms"] = runtime["pull_ms"] + runtime["up_wait_ms"]
        if up.returncode != 0:
            status = "FAIL"
        elif not runtime["healthy"]:
            status = "INCONCLUSIVE"
        else:
            status, rows, labels = _backtest_proof(compose, run, root, state)
    finally:
        try:
            core.run_cmd(compose + ["down", "-v", "--remove-orphans"], run=run, cwd=root)
        except FileNotFoundError:
            pass
        _free_lock(root)
        if prev_term is not None:
            try:
                signal.signal(signal.SIGTERM, prev_term)
            except (ValueError, OSError):
                pass
    _add_check(
        state, core.RUNTIME_CHECK_ID, status, None, runtime["startup_ms"], rows=rows, labels=labels
    )
    state["runtime"] = runtime
    _save_state(state, root)
    print(f"runtime: {status} (rows={rows} labels={labels})")
    return 0 if status == "PASS" else 1


def cmd_receipt(args, run=subprocess.run):
    root = args.root
    state = _load_state(root)
    tree, dirty, diff_hash = core.git_tree_hash(root, run=run)
    commit = core.run_cmd(["git", "-C", root, "rev-parse", "HEAD"], run=run).stdout.strip()
    checks = state.get("checks", [])
    receipt = {
        "schema_version": core.SCHEMA_VERSION,
        "repo": args.repo or os.environ.get("GITHUB_REPOSITORY", ""),
        "commit": commit,
        "head_sha": os.environ.get("PR_HEAD_SHA", ""),
        "tree_hash": tree,
        "dirty": dirty,
        "diff_hash": diff_hash,
        "inputs_digest": core.inputs_digest(root),
        "tool_versions": core.tool_versions(run=run),
        "provider": "compose",
        "sandbox_id": args.project or "",
        "runtime": state.get("runtime", {}),
        "container_health": state.get("container_health", []),
        "checks": checks,
        "features_verified": state.get("features_verified", []),
        "security": state.get("security", []),
        "started_at": state.get("started_at", _now()),
        "finished_at": _now(),
        "result": core.result_of(checks),
    }
    Path(root, ".verify").mkdir(parents=True, exist_ok=True)
    Path(root, RECEIPT).write_text(json.dumps(receipt, indent=2))
    print(f"receipt: {receipt['result']} -> {RECEIPT}")
    return 0 if receipt["result"] == "PASS" else 1


def cmd_check(args, run=subprocess.run):
    p = Path(args.receipt)
    if not p.is_file():
        print("check: receipt missing", file=sys.stderr)
        return 1
    obj = json.loads(p.read_text())
    tree = None
    if not args.expect_tree:  # local mode: recompute against the working tree
        tree, _, _ = core.git_tree_hash(args.root, run=run)
    ok, reason = core.check_receipt(
        obj,
        tree_hash=tree,
        expect_repo=args.expect_repo,
        expect_commit=args.expect_commit,
        expect_tree=args.expect_tree,
        require_clean=args.require_clean,
        require_feature=args.require_feature,
    )
    print(f"check: {'ok' if ok else 'stale/invalid'}: {reason}")
    return 0 if ok else 1


def cmd_clean(args, run=subprocess.run):
    """Tear down every hce-verify-* compose project. Never host-global."""
    try:
        ls = core.run_cmd(["docker", "compose", "ls", "-a", "--format", "json"], run=run)
    except FileNotFoundError:
        print("clean: docker compose plugin missing")
        return 0
    try:
        projects = json.loads(ls.stdout or "[]")
    except json.JSONDecodeError:
        projects = []
    names = [p.get("Name", "") for p in projects if p.get("Name", "").startswith("hce-verify-")]
    for name in names:
        core.run_cmd(["docker", "compose", "-p", name, "down", "-v", "--remove-orphans"], run=run)
    _free_lock(args.root)
    print(f"clean: removed {len(names)} verify project(s)")
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="verify")
    p.add_argument("--root", default=".")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fast")
    sub.add_parser("security")
    rt = sub.add_parser("runtime")
    rt.add_argument("--project", default="")
    rc = sub.add_parser("receipt")
    rc.add_argument("--repo", default="")
    rc.add_argument("--project", default="")
    ck = sub.add_parser("check")
    ck.add_argument("--receipt", default=RECEIPT)
    ck.add_argument("--expect-repo", default=None)
    ck.add_argument("--expect-commit", default=None)
    ck.add_argument("--expect-tree", default=None)
    ck.add_argument("--require-clean", action="store_true")
    ck.add_argument("--require-feature", default=None)
    sub.add_parser("clean")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    return {
        "fast": cmd_fast,
        "security": cmd_security,
        "runtime": cmd_runtime,
        "receipt": cmd_receipt,
        "check": cmd_check,
        "clean": cmd_clean,
    }[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
