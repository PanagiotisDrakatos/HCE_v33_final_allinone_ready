import os

import pytest

pytestmark = [pytest.mark.integration]


@pytest.mark.skipif(os.environ.get("IT_TIMESCALE") != "1", reason="set IT_TIMESCALE=1 to enable")
def test_roundtrip_timescale():
    assert True  # placeholder read-back test
