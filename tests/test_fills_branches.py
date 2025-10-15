import pytest

class Intent:
    def __init__(self, side, typ, qty=1.0, limit_price=None, stop_price=None, queue_pos=0.5):
        self.side = side
        self.type = typ
        self.qty = qty
        self.limit_price = limit_price
        self.stop_price = stop_price
        self.queue_pos = queue_pos

def mk_model(tick=0.01, mode="fixed_ticks", val=1.0, asym=False, seed=42):
    from hcebt.fills import ShadowFillModel
    # Provide a cfg-like object compatible with model's fallback path
    Cfg = type("Cfg", (object,), {
        "slip_mode": mode,
        "slip_value": val,   # mapped to ticks internally
        "rng_seed": seed,
        "bid_ask_aware": True,
    })
    return ShadowFillModel(Cfg())

@pytest.fixture
def snap():
    return {"bid": 100.0, "ask": 100.2, "last": 100.1, "ts": "2024-01-01T00:00:00Z"}


def test_limit_non_marketable_does_not_fill(snap):
    m = mk_model()
    intent = Intent(+1, "limit", qty=1.0, limit_price=snap["ask"] - 0.05)
    price, qty, slip_cost, status = m.limit_fill(snap, intent)
    assert status in ("resting","no_fill")
    assert qty == 0


def test_limit_marketable_respects_clamp(snap):
    m = mk_model()
    intent = Intent(+1, "limit", qty=1.0, limit_price=snap["ask"])
    price, qty, slip_cost, status = m.limit_fill(snap, intent)
    assert price <= intent.limit_price + 1e-12
    assert status in ("filled","partial")


def test_stop_triggers_once(snap):
    m = mk_model()
    intent = Intent(+1, "stop", qty=1.0, stop_price=100.05)
    price, qty, slip_cost, status = m.stop_fill(snap, intent)
    assert status in ("triggered","submitted","filled")


def test_stop_limit_path(snap):
    m = mk_model()
    intent = Intent(+1, "stop-limit", qty=1.0, stop_price=100.05, limit_price=100.25)
    price, qty, slip_cost, status = m.stop_limit_fill(snap, intent)
    assert status in ("triggered","submitted","filled","resting")


def test_zero_spread_market_sell():
    m = mk_model()
    s = {"bid":100.0,"ask":100.0,"last":100.0,"ts":"2024-01-01T00:00:00Z"}
    intent = Intent(-1, "market", qty=1.0)
    price, qty, slip_cost, status = m.market_fill(s, intent)
    assert status == "filled" and qty == 1.0


def test_partial_fill_path_covered(snap):
    m = mk_model(seed=123)
    intent = Intent(+1, "limit", qty=10.0, limit_price=100.2, queue_pos=0.5)
    s = dict(snap, queue_pos=0.5)
    price, qty, slip_cost, status = m.limit_fill(s, intent)
    assert 0.0 <= qty <= 10.0
    assert status in ("partial","filled")

