import os, json, time, numpy as np
from .config import RunConfig, BatchConfig
from .fills import ShadowFillModel, MarketSnapshot, OrderIntent
from .persistence import Repo, RepoConfig
from lib.kahan import KahanSum
from lib.timeutil import to_utc_iso

def run_ab(cfg: RunConfig, A, B):
    # deterministic seed & stable order
    np.random.seed(cfg.fill.seed)
    key = lambda e: (e.get("ts"), e.get("symbol"), e.get("id",0))
    A = sorted(A, key=key); B = sorted(B, key=key)

    # snapshot config
    os.makedirs("run_artifacts", exist_ok=True)
    with open(f"run_artifacts/{cfg.run_id}_config.json","w") as fh:
        json.dump(cfg.model_dump(), fh, indent=2)

    fm = ShadowFillModel(
        slip_mode=cfg.fill.slip_mode, ticks=cfg.fill.ticks, bps=cfg.fill.bps,
        pct_spread=cfg.fill.pct_spread, hybrid_weight=cfg.fill.hybrid_weight,
        bid_ask_aware=cfg.fill.bid_ask_aware, seed=cfg.fill.seed
    )
    repo = Repo(RepoConfig(
        backend=cfg.batch.backend, batch_size=cfg.batch.batch_size,
        flush_interval_ms=cfg.batch.flush_interval_ms, queue_max_batches=cfg.batch.queue_max_batches,
        clickhouse_url=cfg.batch.clickhouse_url, timescale_dsn=cfg.batch.timescale_dsn, table=cfg.batch.table
    ))
    repo.start()

    def simulate(label, data):
        t0 = time.time()
        events = 0
        fills = 0
        partials = 0
        slip_k = KahanSum()
        batch = []
        for ev in data:
            events += 1
            snap = MarketSnapshot(ts=ev["ts"], last=ev["last"], mark=ev.get("mark",ev["last"]), bid=ev["bid"], ask=ev["ask"], spread=ev["ask"]-ev["bid"], volume=ev.get("vol",1.0))
            intent = OrderIntent(side=ev.get("side",1), order_type=ev.get("type","market"), qty=ev.get("qty",1.0), limit_price=ev.get("limit"), stop_price=ev.get("stop"), queue_pos=ev.get("queue_pos",0.5))
            fr = fm.fill(snap, intent)
            if fr.filled_qty>0:
                fills += 1
                if fr.status=="partial": partials += 1
                slip_k.add(fr.slip_cost)
            row = {"run_id":cfg.run_id, "ts":to_utc_iso(ev["ts"]), "symbol":ev["symbol"], "metric":"fill_cost", "value":fr.slip_cost, "label":label}
            batch.append(row)
            if len(batch)>=cfg.batch.batch_size:
                repo.submit(batch); batch=[]
        if batch: repo.submit(batch)
        dur = time.time()-t0
        res = {
            "events": events,
            "fills": fills,
            "partial_fill_ratio": (partials/max(1,fills)),
            "fill_rate": fills/max(1,events),
            "slip_cost": slip_k.value(),
            "events_per_sec": events/max(dur,1e-9),
        }
        return res

    resA = simulate("A", A)
    resB = simulate("B", B)
    repo.stop()
    return {"A":resA,"B":resB,"repo_metrics":repo.metrics}
