from hcebt.fills import MarketSnapshot, OrderIntent, ShadowFillModel


def test_same_seed_same_fill():
    s = MarketSnapshot(ts=0, last=100, bid=99.9, ask=100.1, mark=100.0, spread=0.2, volume=5000)
    intent = OrderIntent(side=-1, order_type="limit", qty=1.0, limit_price=100.1, queue_pos=0.4)
    f1 = ShadowFillModel(seed=42).limit_fill(s, intent)
    f2 = ShadowFillModel(seed=42).limit_fill(s, intent)
    assert f1 == f2
