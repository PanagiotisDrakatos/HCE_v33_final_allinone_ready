"""RunConfig validation: an unknown backend is rejected rather than silently
accepted, so a typo in a run config fails fast instead of writing nowhere."""

from pydantic import ValidationError
import pytest

from hcebt.config import RunConfig


def test_unknown_backend_is_rejected():
    with pytest.raises(ValidationError):
        RunConfig(run_id="t", batch={"backend": "bogus"})


def test_known_backends_accepted():
    for backend in ("none", "clickhouse", "timescale"):
        cfg = RunConfig(run_id="t", batch={"backend": backend})
        assert cfg.batch.backend == backend
