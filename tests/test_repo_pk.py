import pytest
from hcebt.persistence import Repo, RepoConfig


def test_missing_pk_rejected():
    repo = Repo(RepoConfig(backend="none"))
    repo.start()
    with pytest.raises(ValueError):
        repo.submit([{"ts": "2024-01-01T00:00:00+00:00", "symbol": "X", "metric": "fill_cost"}])
    repo.stop()
