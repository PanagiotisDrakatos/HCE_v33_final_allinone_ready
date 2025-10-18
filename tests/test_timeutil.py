from datetime import UTC, datetime

import pytest
from lib.timeutil import to_utc_iso


def test_to_utc_iso_from_seconds_int():
    ts_sec = 1_600_000_000  # 2020-09-13T12:26:40Z
    got = to_utc_iso(ts_sec)
    expected = datetime(2020, 9, 13, 12, 26, 40, tzinfo=UTC).isoformat()
    assert got == expected


def test_to_utc_iso_from_milliseconds_int():
    ts_ms = 1_600_000_000_000  # 2020-09-13T12:26:40Z
    got = to_utc_iso(ts_ms)
    expected = datetime(2020, 9, 13, 12, 26, 40, tzinfo=UTC).isoformat()
    assert got == expected


def test_to_utc_iso_from_iso_string_with_Z():
    s = "2020-09-13T12:26:40Z"
    got = to_utc_iso(s)
    expected = datetime(2020, 9, 13, 12, 26, 40, tzinfo=UTC).isoformat()
    assert got == expected


def test_to_utc_iso_fractional_seconds_float():
    ts_float = 1_600_000_000.5
    got = to_utc_iso(ts_float)
    expected = datetime(2020, 9, 13, 12, 26, 40, 500000, tzinfo=UTC).isoformat()
    assert got == expected


def test_to_utc_iso_invalid_string_raises_value_error():
    with pytest.raises(ValueError):
        to_utc_iso("not-a-valid-timestamp")


def test_to_utc_iso_unsupported_type_raises_type_error():
    with pytest.raises(TypeError):
        to_utc_iso([1, 2, 3])
