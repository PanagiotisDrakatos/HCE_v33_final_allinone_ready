"""Verdict ranking: FAIL < INCONCLUSIVE < PASS, aggregate is the minimum, and
a missing producer never reads as PASS."""

import verify_core as core


def test_min_rank_wins():
    assert core.aggregate(["PASS", "FAIL", "PASS"]) == "FAIL"
    assert core.aggregate(["PASS", "INCONCLUSIVE"]) == "INCONCLUSIVE"
    assert core.aggregate(["PASS", "PASS"]) == "PASS"


def test_empty_is_inconclusive_not_pass():
    assert core.aggregate([]) == "INCONCLUSIVE"
    assert core.result_of([]) == "INCONCLUSIVE"


def test_result_of_checks():
    assert core.result_of([{"status": "PASS"}, {"status": "INCONCLUSIVE"}]) == "INCONCLUSIVE"
    assert core.result_of([{"status": "PASS"}]) == "PASS"


def test_unknown_status_treated_as_inconclusive():
    assert core.result_of([{"status": "weird"}]) == "INCONCLUSIVE"
