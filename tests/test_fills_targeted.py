import math
from dataclasses import dataclass

import pytest

from hcebt.fills import MarketSnapshot, OrderIntent, ShadowFillModel


def make_snap():
    return {
        "ts": 1,
        "last": 100.0,
        "bid": 99.0,
        "ask": 101.0,
        "spread": 2.0,
        "volume": 1000.0,
    }


def test_slip_modes_bid_ask_aware_true_and_false():
    snap = make_snap()

    for bid_ask_aware in (True, False):
        # fixed_ticks
        m = ShadowFillModel(slip_mode="fixed_ticks", ticks=0.5, bid_ask_aware=bid_ask_aware)
        price_buy, *_ = m.market_fill(snap, OrderIntent(side=+1, order_type="market", qty=1))
        price_sell, *_ = m.market_fill(snap, OrderIntent(side=-1, order_type="market", qty=1))
        assert (price_buy - (101.0 if bid_ask_aware else 100.0)) == pytest.approx(0.5)
        assert (price_sell - (99.0 if bid_ask_aware else 100.0)) == pytest.approx(-0.5)

        # bps
        m = ShadowFillModel(slip_mode="bps", bps=10, bid_ask_aware=bid_ask_aware)
        pb, *_ = m.market_fill(snap, OrderIntent(side=+1, order_type="market", qty=2))
        ps, *_ = m.market_fill(snap, OrderIntent(side=-1, order_type="market", qty=2))
        ref_b = 101.0 if bid_ask_aware else 100.0
        ref_s = 99.0 if bid_ask_aware else 100.0
        assert pb == pytest.approx(ref_b + ref_b * (10 / 1e4))
        assert ps == pytest.approx(ref_s - ref_s * (10 / 1e4))

        # pct_spread
        m = ShadowFillModel(slip_mode="pct_spread", pct_spread=50.0, bid_ask_aware=bid_ask_aware)
        pb, *_ = m.market_fill(snap, OrderIntent(side=+1, order_type="market", qty=1))
        ps, *_ = m.market_fill(snap, OrderIntent(side=-1, order_type="market", qty=1))
        assert pb == pytest.approx((101.0 if bid_ask_aware else 100.0) + (2.0 * 0.5))
        assert ps == pytest.approx((99.0 if bid_ask_aware else 100.0) - (2.0 * 0.5))

        # hybrid
        m = ShadowFillModel(
            slip_mode="hybrid", bps=10, pct_spread=50.0, hybrid_weight=0.25, bid_ask_aware=bid_ask_aware
        )
        pb, *_ = m.market_fill(snap, OrderIntent(side=+1, order_type="market", qty=1))
        ps, *_ = m.market_fill(snap, OrderIntent(side=-1, order_type="market", qty=1))
        ref_b = 101.0 if bid_ask_aware else 100.0
        ref_s = 99.0 if bid_ask_aware else 100.0
        s_b = 0.25 * (ref_b * (10 / 1e4)) + 0.75 * (2.0 * 0.5)
        s_s = 0.25 * (ref_s * (10 / 1e4)) + 0.75 * (2.0 * 0.5)
        assert pb == pytest.approx(ref_b + s_b)
        assert ps == pytest.approx(ref_s - s_s)


def test_limit_fill_resting_and_price_capped_by_limit():
    snap = make_snap()
    m = ShadowFillModel(slip_mode="fixed_ticks", ticks=0.2, bid_ask_aware=True)

    # Non-marketable buy (limit below ask)
    p, q, s, st = m.limit_fill(snap, OrderIntent(side=+1, order_type="limit", qty=3, limit_price=100.5))
    assert (p, q, s, st) == (0.0, 0.0, 0.0, "resting")

    # Marketable buy (limit above/equal ask) — price must not exceed limit
    p, q, s, st = m.limit_fill(snap, OrderIntent(side=+1, order_type="limit", qty=3, limit_price=101.1))
    assert st == "filled"
    assert q == 3
    assert p <= 101.1
    assert s == pytest.approx(abs(p - 101.0) * 3)

    # Marketable sell (limit below/equal bid) — price must not go below limit
    p, q, s, st = m.limit_fill(snap, OrderIntent(side=-1, order_type="limit", qty=2, limit_price=98.9))
    assert st == "filled"
    assert q == 2
    assert p >= 98.9
    assert s == pytest.approx(abs(p - 99.0) * 2)


def test_stop_and_stop_limit_paths():
    snap = make_snap()
    m = ShadowFillModel(slip_mode="bps", bps=5.0, bid_ask_aware=True)

    # Stop not triggered
    p, q, s, st = m.stop_fill(snap, OrderIntent(side=+1, order_type="stop", qty=1, stop_price=150))
    assert st == "no_fill"

    # Stop triggered (last >= stop) → uses market_fill
    snap_trig = {**snap, "last": 200.0}
    p, q, s, st = m.stop_fill(snap_trig, OrderIntent(side=+1, order_type="stop", qty=1, stop_price=150))
    assert st == "triggered" and q == 1 and p > 0 and s >= 0

    # Stop-limit triggered but limit not marketable → resting
    p, q, s, st = m.stop_limit_fill(
        snap_trig, OrderIntent(side=+1, order_type="stop-limit", qty=1, stop_price=150, limit_price=100.0)
    )
    assert st == "resting"


def test_fill_dispatch_and_snapshot_mapping():
    # Unknown order type
    snap = make_snap()
    m = ShadowFillModel()
    res = m.fill(snap, OrderIntent(side=+1, order_type="iceberg", qty=1))
    assert res.status == "no_fill" and res.filled_qty == 0

    # Dataclass mapping (spread auto-computed when None)
    @dataclass
    class Snap:
        ts: int = 1
        last: float = 100.0
        bid: float = 99.0
        ask: float = 101.0
        spread: float | None = None
        volume: float = 10.0

    s2 = Snap()
    res = m.fill(s2, OrderIntent(side=-1, order_type="market", qty=4))
    assert res.status == "filled" and res.filled_qty == 4

