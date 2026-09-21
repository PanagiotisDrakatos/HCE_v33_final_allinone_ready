"""Attack table for `verify check` / check_receipt: every binding that must
refuse a stale, forged, or mis-bound receipt."""

import copy

import pytest
import verify_core as core

GOOD = {
    "schema_version": 1,
    "repo": "owner/repo",
    "commit": "c" * 40,
    "head_sha": "",
    "tree_hash": "t" * 40,
    "dirty": False,
    "diff_hash": "",
    "inputs_digest": "d",
    "tool_versions": {},
    "provider": "compose",
    "sandbox_id": "hce-verify-abcd1234-ef01",
    "runtime": {"healthy": True},
    "container_health": [{"name": "timescaledb", "status": "PASS"}],
    "checks": [
        {"id": "ruff-format", "ok": True, "status": "PASS"},
        {"id": "ruff-check", "ok": True, "status": "PASS"},
        {"id": "pytest", "ok": True, "status": "PASS"},
        {"id": "runtime-timescale", "ok": True, "status": "PASS"},
    ],
    "features_verified": ["timescale-roundtrip"],
    "security": [],
    "started_at": "a",
    "finished_at": "b",
    "result": "PASS",
}


def g(**over):
    r = copy.deepcopy(GOOD)
    r.update(over)
    return r


def test_valid_receipt_passes():
    ok, reason = core.check_receipt(
        g(), expect_tree="t" * 40, require_feature="timescale-roundtrip"
    )
    assert ok, reason


def test_tree_mismatch_is_fail():
    ok, reason = core.check_receipt(g(), expect_tree="OTHER")
    assert not ok and reason == "tree mismatch"


def test_repo_mismatch_is_fail():
    ok, reason = core.check_receipt(g(), expect_repo="someone/else")
    assert not ok and reason == "repo mismatch"


def test_commit_mismatch_is_fail():
    ok, reason = core.check_receipt(g(), expect_commit="d" * 40)
    assert not ok and reason == "commit mismatch"


def test_stale_when_worktree_tree_differs():
    ok, reason = core.check_receipt(g(), tree_hash="NEWTREE")
    assert not ok and "stale" in reason


def test_dirty_rejected_when_clean_required():
    ok, reason = core.check_receipt(g(dirty=True), require_clean=True)
    assert not ok and reason == "dirty worktree"


def test_fast_only_receipt_rejected_by_feature_requirement():
    ok, reason = core.check_receipt(g(features_verified=[]), require_feature="timescale-roundtrip")
    assert not ok and "timescale-roundtrip" in reason


def test_non_pass_result_rejected():
    ok, reason = core.check_receipt(g(result="INCONCLUSIVE"))
    assert not ok and "INCONCLUSIVE" in reason


@pytest.mark.parametrize("missing", list(core._REQUIRED_KEYS))
def test_each_required_key_removal_is_rejected(missing):
    bad = g()
    del bad[missing]
    ok, reason = core.check_receipt(bad)
    assert not ok and "invalid receipt" in reason


def test_pass_with_empty_checks_rejected():
    ok, reason = core.check_receipt(g(checks=[], result="PASS"))
    assert not ok


def test_pass_missing_required_check_rejected():
    only_pytest = [{"id": "pytest", "ok": True, "status": "PASS"}]
    ok, reason = core.check_receipt(g(checks=only_pytest))
    assert not ok
