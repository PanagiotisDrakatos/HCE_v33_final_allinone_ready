import logging
from typing import Dict, List
from dataclasses import dataclass
import threading, time, queue

@dataclass
class RepoConfig:
    backend: str = "none"   # none|clickhouse|timescale
    batch_size: int = 5000
    flush_interval_ms: int = 500
    queue_max_batches: int = 200
    clickhouse_url: str = "http://localhost:8123"
    timescale_dsn: str = "postgresql://postgres:postgres@localhost:5432/hce"
    table: str = "market_signals"

class Repo:
    def __init__(self, cfg: RepoConfig):
        self.cfg = cfg
        self.metrics = {"dropped_batches":0, "batch_retry_count":0, "write_latency_ms":0.0}
        self.q = queue.Queue(maxsize=cfg.queue_max_batches)
        self.stop_flag = False
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.repo = None
        if cfg.backend == "clickhouse":
            from clickhouse_connect import get_client
            host = cfg.clickhouse_url.split('://')[-1].split(':')[0]
            port = int(cfg.clickhouse_url.split(':')[-1]) if ':' in cfg.clickhouse_url else 8123
            self.repo = ("ch", get_client(host=host, port=port))
        elif cfg.backend == "timescale":
            import psycopg
            self.repo = ("ts", psycopg.connect(cfg.timescale_dsn))
            self.repo[1].autocommit = True

    def start(self): self.thread.start()
    def stop(self):
        self.stop_flag = True
        self.thread.join(timeout=max(2.0, self.cfg.flush_interval_ms/1000 + 1.0))
        if self.repo and self.repo[0]=="ts":
            self.repo[1].close()

    def submit(self, rows: List[Dict]):
        # enforce PK presence
        for r in rows:
            for k in ("run_id","ts","symbol","metric"):
                if k not in r: raise ValueError(f"Missing key {k} in row")
        try:
            self.q.put_nowait(rows)
        except queue.Full:
            self.metrics["dropped_batches"] += 1

    def _flush(self, rows: List[Dict]):
        # in-batch dedupe by PK
        seen = set(); out = []
        for r in rows:
            key = (r["run_id"], r["ts"], r["symbol"], r["metric"])
            if key in seen: continue
            seen.add(key); out.append(r)
        t0 = time.time()
        ok = False; attempts = 0
        while not ok and attempts < 5:
            try:
                if not self.repo or self.repo[0]=="noop":
                    ok = True
                elif self.repo[0]=="ch":
                    cols = sorted(out[0].keys())
                    data = [[r.get(c) for c in cols] for r in out]
                    self.repo[1].insert(self.cfg.table, data, column_names=cols)
                    ok = True
                elif self.repo[0]=="ts":
                    cols = sorted(out[0].keys())
                    vals = ','.join(['(' + ','.join(['%s']*len(cols)) + ')'] * len(out))
                    args = []
                    for r in out: args.extend([r.get(c) for c in cols])
                    cols_sql = ','.join(cols)
                    pk_cols = "run_id,ts,symbol,metric"
                    sql = f"INSERT INTO {self.cfg.table} ({cols_sql}) VALUES {vals} ON CONFLICT ({pk_cols}) DO UPDATE SET " + ','.join([f"{c}=EXCLUDED.{c}" for c in cols if c not in ('run_id','ts','symbol','metric')])
                    with self.repo[1].cursor() as cur:
                        cur.execute(sql, args)
                    ok = True
            except Exception:
                attempts += 1
                self.metrics["batch_retry_count"] += 1
                time.sleep(min(1.0, 0.2 * (2 ** max(0, attempts-1))))
        self.metrics["write_latency_ms"] = (time.time()-t0)*1000.0

    def _loop(self):
        buf = []
        last = time.time()
        while not self.stop_flag:
            timeout = max(0.0, self.cfg.flush_interval_ms/1000 - (time.time()-last))
            try:
                rows = self.q.get(timeout=timeout)
                buf.extend(rows)
                if len(buf) >= self.cfg.batch_size:
                    self._flush(buf); buf=[]; last=time.time()
            except queue.Empty:
                if buf:
                    self._flush(buf); buf=[]; last=time.time()

        if not ok:
            logging.error('failed to flush %d rows after %d attempts', len(rows), attempts)

    # Final flush on stop
    try:
        buf = locals().get('buf', [])
        if buf:
            self._flush(buf)
    except Exception as _e:
        logging.warning('final flush error: %s', _e)
    ### FINAL_FLUSH_MARKER ###