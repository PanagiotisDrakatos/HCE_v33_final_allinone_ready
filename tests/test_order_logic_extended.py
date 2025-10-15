import pytest

@pytest.fixture
def snap():
    return {"bid": 100.0, "ask": 100.2, "last": 100.1, "ts": "2024-01-01T00:00:00Z"}

class Intent:
    def __init__(self, side, typ, limit_price=None, stop_price=None, qty=1.0):
        self.side = side  # +1 buy, -1 sell
        self.type = typ   # 'market'|'limit'|'stop'|'stop-limit'
        self.limit_price = limit_price
        self.stop_price = stop_price
        self.qty = qty

def mk_model():
    from hcebt.fills import ShadowFillModel
    class Cfg:
        tick_size=0.01; slip_mode="fixed_ticks"; slip_value=1.0; asym_break=False; rng_seed=42
    return ShadowFillModel(Cfg())

def test_market_buy_fill_price_equals_ask_clamped(snap):
    m = mk_model()
    intent = Intent(side=+1, typ="market", qty=1.0)
    price, qty, slip_cost, status = m.market_fill(snap, intent)
    assert price >= snap["ask"] - 1e-12
    assert qty == pytest.approx(1.0)
    assert status == "filled"

def test_non_marketable_limit_does_not_fill(snap):
    m = mk_model()
    intent = Intent(side=+1, typ="limit", limit_price=snap["ask"] - 0.05, qty=1.0)
    price, qty, slip_cost, status = m.limit_fill(snap, intent)
    assert status in ("resting","no_fill")
    assert qty == 0.0

def test_marketable_limit_respects_limit_clamp(snap):
    m = mk_model()
    intent = Intent(side=+1, typ="limit", limit_price=snap["ask"], qty=1.0)
    price, qty, slip_cost, status = m.limit_fill(snap, intent)
    assert price <= intent.limit_price + 1e-12
    assert qty > 0.0
    assert status in ("filled","partial")

def test_zero_spread_handling():
    m = mk_model()
    snap = {"bid": 100.0, "ask": 100.0, "last": 100.0, "ts": "2024-01-01T00:00:00Z"}
    intent = Intent(side=-1, typ="market", qty=1.0)
    price, qty, slip_cost, status = m.market_fill(snap, intent)
    assert qty == pytest.approx(1.0)
    assert status == "filled"
