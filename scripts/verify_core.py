#!/usr/bin/env python3
"""Pure, testable core for the verification kernel: hashing, verdict ranking,
producer-output parsing, and receipt validation. No side effects beyond git
reads and a temporary index file. Standard library only.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

RANK = {"FAIL": 0, "INCONCLUSIVE": 1, "PASS": 2}
SCHEMA_VERSION = 1
REQUIRED_CHECK_IDS = ("ruff-format", "ruff-check", "pytest")
RUNTIME_CHECK_ID = "runtime-timescale"
RUNTIME_FEATURE = "timescale-roundtrip"
# The fixtures write 2 rows labelled A and 2 labelled B; assert the exact
# distribution so a swapped or partial write cannot pass on cardinality alone.
TIMESCALE_EXPECTED = {"A": 2, "B": 2}
INPUTS = (
    "requirements.txt",
    "requirements-dev.txt",
    "docker-compose.yml",
    "compose.verify.yml",
    "scripts/verify.py",
    "scripts/verify_core.py",
    ".github/workflows/ci.yml",
    "pyproject.toml",
    "pytest.ini",
)


def run_cmd(cmd, run=subprocess.run, **kw):
    """Run a command capturing text. `run` is injectable for tests."""
    kw.setdefault("capture_output", True)
    kw.setdefault("text", True)
    return run(cmd, **kw)


# --------------------------------------------------------------------------- #
# hashing / identity                                                          #
# --------------------------------------------------------------------------- #
def git_tree_hash(root=".", run=subprocess.run):
    """Return (tree_hash, dirty, diff_hash).

    Clean: tree_hash = `git rev-parse HEAD^{tree}`, diff_hash "".
    Dirty: tree_hash = `git write-tree` over a temp index seeded from the real
    index plus all working-tree changes; diff_hash = sha256 of `git diff HEAD`.
    """
    root = Path(root)
    porcelain = run_cmd(["git", "-C", str(root), "status", "--porcelain"], run=run)
    if not porcelain.stdout.strip():
        tree = run_cmd(["git", "-C", str(root), "rev-parse", "HEAD^{tree}"], run=run).stdout.strip()
        return tree, False, ""
    diff = run_cmd(["git", "-C", str(root), "diff", "HEAD"], run=run).stdout
    diff_hash = hashlib.sha256(diff.encode()).hexdigest()
    real_index = root / ".git" / "index"
    tmp = tempfile.NamedTemporaryFile(prefix="verify-index-", delete=False)
    tmp.close()
    try:
        if real_index.exists():
            shutil.copyfile(real_index, tmp.name)
        env = {**os.environ, "GIT_INDEX_FILE": tmp.name}
        run_cmd(["git", "-C", str(root), "add", "-A"], run=run, env=env)
        tree = run_cmd(["git", "-C", str(root), "write-tree"], run=run, env=env).stdout.strip()
    finally:
        os.unlink(tmp.name)
    return tree, True, diff_hash


def inputs_digest(root=".", files=INPUTS):
    """sha256 over the declared input files; a missing file still changes it."""
    h = hashlib.sha256()
    root = Path(root)
    for rel in files:
        p = root / rel
        h.update(rel.encode())
        h.update(b"\0")
        h.update(p.read_bytes() if p.is_file() else b"\0MISSING\0")
        h.update(b"\0")
    return h.hexdigest()


def tool_versions(run=subprocess.run):
    out = {}
    probes = {
        "python": [sys.executable, "--version"],
        "ruff": ["ruff", "--version"],
        "pytest": ["pytest", "--version"],
        "docker": ["docker", "--version"],
        "compose": ["docker", "compose", "version", "--short"],
    }
    for name, cmd in probes.items():
        try:
            r = run_cmd(cmd, run=run)
            text = (r.stdout or r.stderr or "").strip()
            out[name] = text.splitlines()[0] if text else ""
        except (FileNotFoundError, OSError):
            out[name] = ""
    return out


# --------------------------------------------------------------------------- #
# verdict                                                                     #
# --------------------------------------------------------------------------- #
def _status_from_min(min_rank):
    for k, v in RANK.items():
        if v == min_rank:
            return k
    return "INCONCLUSIVE"


def aggregate(statuses):
    """Minimum rank over statuses. Empty -> INCONCLUSIVE (no producer)."""
    ranks = [RANK[s] for s in statuses if s in RANK]
    return _status_from_min(min(ranks)) if ranks else "INCONCLUSIVE"


def result_of(checks):
    """Aggregate over a list of check dicts."""
    if not checks:
        return "INCONCLUSIVE"
    ranks = [RANK.get(c.get("status", "INCONCLUSIVE"), 1) for c in checks]
    return _status_from_min(min(ranks))


def parse_junit(text):
    """Return (collected, skipped, status) from JUnit XML.

    Zero collected or all-skipped -> INCONCLUSIVE; any failure/error -> FAIL;
    else PASS. Never trusts an exit code alone.
    """
    import xml.etree.ElementTree as ET

    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return 0, 0, "INCONCLUSIVE"
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    tests = sum(int(s.get("tests", 0)) for s in suites)
    skipped = sum(int(s.get("skipped", 0)) for s in suites)
    failures = sum(int(s.get("failures", 0)) for s in suites)
    errors = sum(int(s.get("errors", 0)) for s in suites)
    if tests == 0 or skipped == tests:
        return tests, skipped, "INCONCLUSIVE"
    if failures or errors:
        return tests, skipped, "FAIL"
    return tests, skipped, "PASS"


def parse_compose_health(ps_json):
    """Health per service from `docker compose ps --format json`.

    Missing/empty or 'starting' -> INCONCLUSIVE; 'healthy' -> PASS; else FAIL.
    """
    import json

    txt = ps_json.strip()
    if not txt:
        return []
    rows = (
        json.loads(txt)
        if txt.startswith("[")
        else [json.loads(line) for line in txt.splitlines() if line.strip()]
    )
    out = []
    for r in rows:
        health = (r.get("Health") or "").lower()
        name = r.get("Name") or r.get("Service") or "?"
        if health == "healthy":
            status = "PASS"
        elif health in ("", "starting"):
            status = "INCONCLUSIVE"
        else:
            status = "FAIL"
        out.append({"name": name, "health": health or "none", "status": status})
    return out


# --------------------------------------------------------------------------- #
# receipt validation / check                                                  #
# --------------------------------------------------------------------------- #
_REQUIRED_KEYS = {
    "schema_version": int,
    "repo": str,
    "commit": str,
    "tree_hash": str,
    "dirty": bool,
    "diff_hash": str,
    "inputs_digest": str,
    "tool_versions": dict,
    "provider": str,
    "sandbox_id": str,
    "runtime": dict,
    "container_health": list,
    "checks": list,
    "features_verified": list,
    "security": list,
    "started_at": str,
    "finished_at": str,
    "result": str,
}


def validate_receipt(obj):
    """Return a list of error strings; empty means schema-valid."""
    if not isinstance(obj, dict):
        return ["receipt is not an object"]
    errs = []
    for key, typ in _REQUIRED_KEYS.items():
        if key not in obj:
            errs.append(f"missing key: {key}")
        elif not isinstance(obj[key], typ):
            errs.append(f"wrong type: {key}")
    if obj.get("result") not in RANK:
        errs.append("result not in {PASS,FAIL,INCONCLUSIVE}")
    if isinstance(obj.get("checks"), list) and len(obj["checks"]) < 1:
        errs.append("checks: minItems 1")
    # A PASS receipt must have every check it contains marked ok. Which checks a
    # receipt is expected to carry is a caller policy, not a schema rule: a
    # single `make verify` receipt holds the fast + runtime checks, while the
    # CI runtime-verify lane produces a runtime-only receipt (the fast/unit
    # lanes are separate required jobs the aggregate checks via needs.*.result,
    # and the runtime proof is enforced with --require-feature).
    if obj.get("result") == "PASS":
        for c in obj.get("checks", []):
            if isinstance(c, dict) and not c.get("ok"):
                errs.append(f"PASS but check not ok: {c.get('id')}")
    return errs


def check_receipt(
    obj,
    tree_hash=None,
    expect_repo=None,
    expect_commit=None,
    expect_tree=None,
    require_clean=False,
    require_feature=None,
):
    """Return (ok, reason). Schema + result==PASS + every requested binding."""
    errs = validate_receipt(obj)
    if errs:
        return False, "invalid receipt: " + "; ".join(errs)
    if obj["result"] != "PASS":
        return False, f"result is {obj['result']}"
    if expect_repo is not None and obj.get("repo") != expect_repo:
        return False, "repo mismatch"
    if expect_commit is not None and obj.get("commit") != expect_commit:
        return False, "commit mismatch"
    if expect_tree is not None and obj.get("tree_hash") != expect_tree:
        return False, "tree mismatch"
    if tree_hash is not None and obj.get("tree_hash") != tree_hash:
        return False, "stale receipt: tree changed"
    if require_clean and obj.get("dirty"):
        return False, "dirty worktree"
    if require_feature:
        if require_feature not in obj.get("features_verified", []):
            return False, f"feature {require_feature} not verified"
        # The feature string is not enough: require the runtime check that backs
        # it to be present and ok, so features_verified cannot claim a proof no
        # check supports.
        runtime_ok = any(
            isinstance(c, dict) and c.get("id") == RUNTIME_CHECK_ID and c.get("ok")
            for c in obj.get("checks", [])
        )
        if not runtime_ok:
            return False, f"feature {require_feature} has no passing {RUNTIME_CHECK_ID} check"
    return True, "ok"
