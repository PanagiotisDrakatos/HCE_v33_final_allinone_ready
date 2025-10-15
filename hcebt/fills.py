from dataclasses import dataclass
from typing import Optional, Any, Mapping, Tuple
import numpy as np

@dataclass
class MarketSnapshot:
    ts: int
    last: float
    mark: float
    bid: float
    ask: float
    spread: float
    volume: float

@dataclass
class OrderIntent:
    side: int  # +1 buy, -1 sell
    order_type: str  # market|limit|stop|stop-limit
    qty: float
    limit_price: Optional[float]=None
    stop_price: Optional[float]=None
    tif: str = "GTC"
    queue_pos: float = 0.5  # 0=front,1=back

# Return type alias used by public fill methods
FillTuple = Tuple[float, float, float, str]

@dataclass
class FillResult:
    price: float
    filled_qty: float
    slip_cost: float
    status: str

class ShadowFillModel:
    def __init__(self, slip_mode: Any = "bps", ticks: float = 1.0, bps: float = 2.0, pct_spread: float = 0.5, hybrid_weight: float = 0.5, bid_ask_aware: bool=True, seed: int=42):
        # Allow passing a config object as the first positional arg
        if not isinstance(slip_mode, str) and hasattr(slip_mode, "slip_mode"):
            cfg = slip_mode
            slip_mode = getattr(cfg, "slip_mode", "bps")
            # tests provide tick_size and slip_value
            ticks = getattr(cfg, "slip_value", ticks)
            seed = getattr(cfg, "rng_seed", seed)
            # optional extras if present
            bid_ask_aware = getattr(cfg, "bid_ask_aware", bid_ask_aware)
        self.slip_mode = str(slip_mode)
        self.ticks = float(ticks)
        self.bps = float(bps)
        self.pct_spread = float(pct_spread)
        self.hybrid_weight = float(hybrid_weight)
        self.bid_ask_aware = bool(bid_ask_aware)
        self.rng = np.random.default_rng(int(seed))

    def _slip(self, snap: Mapping[str, Any], side: int) -> float:
        bid = float(snap.get("bid", snap.get("last", 0.0)))
        ask = float(snap.get("ask", snap.get("last", 0.0)))
        last = float(snap.get("last", (bid + ask) / 2 if (bid or ask) else 0.0))
        spread = float(snap.get("spread", max(0.0, ask - bid)))
        ref = last if not self.bid_ask_aware else (ask if side>0 else bid)
        if self.slip_mode == "fixed_ticks":
            return self.ticks * (1 if side>0 else -1)
        elif self.slip_mode == "bps":
            s = ref * (self.bps/1e4)
            return s if side>0 else -s
        elif self.slip_mode == "pct_spread":
            s = spread * (self.pct_spread/100.0)
            return s if side>0 else -s
        elif self.slip_mode == "hybrid":
            s_bps = ref * (self.bps/1e4)
            s_sp  = spread * (self.pct_spread/100.0)
            s = self.hybrid_weight*s_bps + (1-self.hybrid_weight)*s_sp
            return s if side>0 else -s
        return 0.0

    def _prob_limit_fill(self, snap: Mapping[str, Any], intent: Any) -> float:
        bid = float(snap.get("bid", 0.0)); ask = float(snap.get("ask", 0.0))
        touch = ask if getattr(intent, 'side', 1) > 0 else bid
        limit_price = getattr(intent, 'limit_price', None)
        if limit_price is None:
            return 0.0
        price_edge = (touch - limit_price) if intent.side>0 else (limit_price - touch)
        spread = float(snap.get("spread", max(0.0, ask - bid)))
        last = float(snap.get("last", (bid + ask) / 2 if (bid or ask) else 0.0))
        edge_score = 1.0 if price_edge>=0 else max(0.0, 1.0 + price_edge/max(spread,1e-9))
        vol = float(snap.get("volume", 0.0))
        ref = max(touch, 1e-9)
        vol_score = 1.0 - float(np.exp(-vol / ref))
        queue_pos = float(getattr(intent, 'queue_pos', 0.5))
        queue_score = 1.0 - queue_pos
        prob = 0.3*edge_score + 0.4*vol_score + 0.3*queue_score
        return float(max(0.0, min(1.0, prob)))

    def _snap_to_mapping(self, snap: Any) -> Mapping[str, Any]:
        if isinstance(snap, dict):
            return snap
        # assume dataclass-like
        return {
            "ts": getattr(snap, 'ts', 0),
            "last": getattr(snap, 'last', 0.0),
            "mark": getattr(snap, 'mark', getattr(snap, 'last', 0.0)),
            "bid": getattr(snap, 'bid', getattr(snap, 'last', 0.0)),
            "ask": getattr(snap, 'ask', getattr(snap, 'last', 0.0)),
            "spread": getattr(snap, 'spread', None) if getattr(snap, 'spread', None) is not None else max(0.0, getattr(snap, 'ask', 0.0) - getattr(snap, 'bid', 0.0)),
            "volume": getattr(snap, 'volume', 0.0),
        }

    def market_fill(self, snap: Any, intent: Any) -> FillTuple:
        s = self._snap_to_mapping(snap)
        side = int(getattr(intent, 'side', 1))
        qty = float(getattr(intent, 'qty', 0.0))
        bid = float(s.get("bid", 0.0)); ask = float(s.get("ask", 0.0)); last = float(s.get("last", 0.0))
        ref = last if not self.bid_ask_aware else (ask if side>0 else bid)
        slip = self._slip(s, side)
        price = ref + slip
        slip_cost = abs(slip) * qty
        return (price, qty, slip_cost, "filled")

    def limit_fill(self, snap: Any, intent: Any) -> FillTuple:
        s = self._snap_to_mapping(snap)
        side = int(getattr(intent, 'side', 1))
        qty = float(getattr(intent, 'qty', 0.0))
        limit_price = getattr(intent, 'limit_price', None)
        bid = float(s.get("bid", 0.0)); ask = float(s.get("ask", 0.0))
        if limit_price is None:
            return (0.0, 0.0, 0.0, "no_fill")
        touch = ask if side>0 else bid
        marketable = (side>0 and limit_price>=touch) or (side<0 and limit_price<=touch)
        # Non-marketable limit orders rest; do not fill now
        if not marketable:
            return (0.0, 0.0, 0.0, "resting")
        # Marketable: execute at touch plus slip but never violate the limit price
        slip = self._slip(s, side)
        raw_price = touch + slip
        if side > 0:
            price = min(raw_price, float(limit_price))
        else:
            price = max(raw_price, float(limit_price))
        filled = qty
        # Use actual distance from touch as slip cost
        slip_cost = abs(price - touch) * filled
        status = "filled"
        return (price, filled, slip_cost, status)

    def stop_fill(self, snap: Any, intent: Any) -> FillTuple:
        s = self._snap_to_mapping(snap)
        stop_price = getattr(intent, 'stop_price', None)
        if stop_price is None:
            return (0.0, 0.0, 0.0, "no_fill")
        side = int(getattr(intent, 'side', 1))
        last = float(s.get("last", 0.0))
        trig = (side>0 and last>=stop_price) or (side<0 and last<=stop_price)
        if not trig:
            return (0.0, 0.0, 0.0, "no_fill")
        price, qty, slip_cost, _ = self.market_fill(s, intent)
        return (price, qty, slip_cost, "triggered")

    def stop_limit_fill(self, snap: Any, intent: Any) -> FillTuple:
        s = self._snap_to_mapping(snap)
        stop_price = getattr(intent, 'stop_price', None)
        if stop_price is None:
            return (0.0, 0.0, 0.0, "no_fill")
        side = int(getattr(intent, 'side', 1))
        last = float(s.get("last", 0.0))
        trig = (side>0 and last>=stop_price) or (side<0 and last<=stop_price)
        if not trig:
            return (0.0, 0.0, 0.0, "no_fill")
        return self.limit_fill(s, intent)

    def fill(self, snap: Any, intent: Any) -> FillResult:
        ot = getattr(intent, 'order_type', getattr(intent, 'type', 'market'))
        if ot=="market":
            p,q,s,st = self.market_fill(snap, intent)
        elif ot=="limit":
            p,q,s,st = self.limit_fill(snap, intent)
        elif ot=="stop":
            p,q,s,st = self.stop_fill(snap, intent)
        elif ot=="stop-limit":
            p,q,s,st = self.stop_limit_fill(snap, intent)
        else:
            p,q,s,st = (0.0,0.0,0.0,"no_fill")
        return FillResult(price=p, filled_qty=q, slip_cost=s, status=st)
