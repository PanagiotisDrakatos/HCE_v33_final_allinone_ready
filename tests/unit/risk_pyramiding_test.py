import math

from src.risk.pyramiding import PyramidingConfig, next_size


def test_risk_neutral_constant_size():
    cfg = PyramidingConfig(max_layers=3, risk_neutral=True)
    assert next_size(0, 100, cfg) == 100
    assert next_size(1, 100, cfg) == 100
    assert next_size(2, 100, cfg) == 100
    assert next_size(3, 100, cfg) == 0.0


def test_aggressive_geometric_increase():
    cfg = PyramidingConfig(max_layers=3, risk_neutral=False)
    assert math.isclose(next_size(0, 100, cfg), 100)
    assert math.isclose(next_size(1, 100, cfg), 125)
    assert math.isclose(next_size(2, 100, cfg), 150)
    assert next_size(3, 100, cfg) == 0.0
