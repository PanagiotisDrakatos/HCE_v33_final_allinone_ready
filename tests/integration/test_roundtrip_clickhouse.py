import os, pytest
pytestmark = [pytest.mark.integration]

@pytest.mark.skipif(os.environ.get("IT_CLICKHOUSE") != "1", reason="set IT_CLICKHOUSE=1 to enable")
def test_roundtrip_clickhouse():
    assert True  # placeholder read-back test
