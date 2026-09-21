"""Producer-output parsers: a check with no usable output is INCONCLUSIVE, an
unhealthy or still-starting container is not proof, and a failed test run is a
FAIL — never inferred from an exit code alone."""

import verify_core as core


def test_junit_pass():
    assert core.parse_junit('<testsuite tests="3" failures="0" errors="0" skipped="0"/>') == (
        3,
        0,
        "PASS",
    )


def test_junit_zero_collected_is_inconclusive():
    assert core.parse_junit('<testsuite tests="0" failures="0" errors="0" skipped="0"/>')[2] == (
        "INCONCLUSIVE"
    )


def test_junit_all_skipped_is_inconclusive():
    assert core.parse_junit('<testsuite tests="2" failures="0" errors="0" skipped="2"/>')[2] == (
        "INCONCLUSIVE"
    )


def test_junit_failure_is_fail():
    assert core.parse_junit('<testsuite tests="2" failures="1" errors="0" skipped="0"/>')[2] == (
        "FAIL"
    )


def test_junit_garbage_is_inconclusive():
    assert core.parse_junit("not xml")[2] == "INCONCLUSIVE"


def test_health_healthy_is_pass():
    h = core.parse_compose_health('{"Name":"ts","Health":"healthy"}')
    assert h[0]["status"] == "PASS"


def test_health_starting_is_inconclusive():
    h = core.parse_compose_health('{"Name":"ts","Health":"starting"}')
    assert h[0]["status"] == "INCONCLUSIVE"


def test_health_absent_is_inconclusive():
    h = core.parse_compose_health('{"Name":"ts","Health":""}')
    assert h[0]["status"] == "INCONCLUSIVE"


def test_health_unhealthy_is_fail():
    h = core.parse_compose_health('{"Name":"ts","Health":"unhealthy"}')
    assert h[0]["status"] == "FAIL"


def test_health_empty_output_is_no_rows():
    assert core.parse_compose_health("") == []


def test_health_json_array_form():
    h = core.parse_compose_health('[{"Name":"a","Health":"healthy"},{"Name":"b","Health":""}]')
    assert [x["status"] for x in h] == ["PASS", "INCONCLUSIVE"]
