from dataclasses import dataclass
from typing import Optional
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

@dataclass
class FillResult:
    filled_qty: float
    avg_price: float
    slip_cost: float
    status: str  # filled|partial|no_fill|triggered

class ShadowFillModel:
    def __init__(self, slip_mode: str = "bps", ticks: float = 1.0, bps: float = 2.0, pct_spread: float = 0.5, hybrid_weight: float = 0.5, bid_ask_aware: bool=True, seed: int=42):
        self.slip_mode = slip_mode
        self.ticks = ticks
        self.bps = bps
        self.pct_spread = pct_spread
        self.hybrid_weight = hybrid_weight
        self.bid_ask_aware = bid_ask_aware
        self.rng = np.random.default_rng(seed)

    def _slip(self, snap: MarketSnapshot, side: int) -> float:
        spread = max(snap.spread, 1e-9)
        ref = snap.last if not self.bid_ask_aware else (snap.ask if side>0 else snap.bid)
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

    def _prob_limit_fill(self, snap: MarketSnapshot, intent: OrderIntent) -> float:
        touch = snap.ask if intent.side>0 else snap.bid
        if intent.limit_price is None: return 0.0
        price_edge = (touch - intent.limit_price) if intent.side>0 else (intent.limit_price - touch)
        edge_score = 1.0 if price_edge>=0 else max(0.0, 1.0 + price_edge/max(snap.spread,1e-9))
        vol_score = 1.0 - np.exp(-snap.volume / max(touch,1e-9))
        queue_score = 1.0 - intent.queue_pos
        prob = 0.3*edge_score + 0.4*vol_score + 0.3*queue_score
        return float(max(0.0, min(1.0, prob)))

    def market_fill(self, snap: MarketSnapshot, intent: OrderIntent) -> FillResult:
        ref = snap.last if not self.bid_ask_aware else (snap.ask if intent.side>0 else snap.bid)
        slip = self._slip(snap, intent.side)
        price = ref + slip
        slip_cost = abs(slip) * intent.qty
        return FillResult(intent.qty, price, slip_cost, "filled")

    def limit_fill(self, snap: MarketSnapshot, intent: OrderIntent) -> FillResult:
        touch = snap.ask if intent.side>0 else snap.bid
        if intent.limit_price is None: return FillResult(0.0,0.0,0.0,"no_fill")
        marketable = (intent.side>0 and intent.limit_price>=touch) or (intent.side<0 and intent.limit_price<=touch)
        prob = 1.0 if marketable else self._prob_limit_fill(snap, intent)
        if prob <= 0.0: return FillResult(0.0,0.0,0.0,"no_fill")
        filled = intent.qty if prob>=1.0 else float(self.rng.binomial(1000, prob)/1000.0 * intent.qty)
        if filled <= 0.0: return FillResult(0.0,0.0,0.0,"no_fill")
        base = min(intent.limit_price, touch) if intent.side>0 else max(intent.limit_price, touch)
        slip = self._slip(snap, intent.side)
        price = base + slip
            # Clamp: respect limit price when not marketable
            if not marketable:
                if intent.side > 0:
                    price = min(price, intent.limit_price)
                else:
                    price = max(price, intent.limit_price)
        slip_cost = abs(slip) * filled
        status = "filled" if filled>=intent.qty-1e-9 else "partial"
        return FillResult(filled, price, slip_cost, status)

    def stop_fill(self, snap: MarketSnapshot, intent: OrderIntent) -> FillResult:
        if intent.stop_price is None: return FillResult(0.0,0.0,0.0,"no_fill")
        trig = (intent.side>0 and snap.last>=intent.stop_price) or (intent.side<0 and snap.last<=intent.stop_price)
        if not trig: return FillResult(0.0,0.0,0.0,"no_fill")
        fr = self.market_fill(snap, intent); fr.status = "triggered"; return fr

    def stop_limit_fill(self, snap: MarketSnapshot, intent: OrderIntent) -> FillResult:
        if intent.stop_price is None: return FillResult(0.0,0.0,0.0,"no_fill")
        trig = (intent.side>0 and snap.last>=intent.stop_price) or (intent.side<0 and snap.last<=intent.stop_price)
        if not trig: return FillResult(0.0,0.0,0.0,"no_fill")
        return self.limit_fill(snap, intent)

    def fill(self, snap: MarketSnapshot, intent: OrderIntent) -> FillResult:
        ot = intent.order_type
        if ot=="market": return self.market_fill(snap, intent)
        if ot=="limit": return self.limit_fill(snap, intent)
        if ot=="stop": return self.stop_fill(snap, intent)
        if ot=="stop-limit": return self.stop_limit_fill(snap, intent)
        return FillResult(0.0,0.0,0.0,"no_fill")