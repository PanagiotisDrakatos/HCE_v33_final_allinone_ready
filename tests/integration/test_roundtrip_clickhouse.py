import pytest

pytestmark = [pytest.mark.integration]


def test_roundtrip_clickhouse():
    """ClickHouse round-trip is deferred: the verify-plane change proves the
    Timescale path (see openspec/changes/verify-plane-v0). ClickHouse carries
    open questions (empty password, ISO string into DateTime64, init.sql
    execution) that need their own change. This is an explicit deferral, not a
    silent placeholder pass."""
    pytest.skip("ClickHouse round-trip deferred to a later change")
