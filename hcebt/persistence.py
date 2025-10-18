from dataclasses import dataclass
import logging
import queue
import threading
import time


@dataclass
class RepoConfig:
    backend: str = "none"  # none|clickhouse|timescale
    batch_size: int = 5000
    flush_interval_ms: int = 500
    # accept both queue_max and queue_max_batches for compatibility
    queue_max: int = 200
    queue_max_batches: int | None = None
    clickhouse_url: str = "http://localhost:8123"
    timescale_dsn: str = "postgresql://postgres:postgres@localhost:5432/hce"
    table: str = "market_signals"

    def __post_init__(self):
        if self.queue_max_batches is not None:
            # keep values in sync, prefer explicit queue_max_batches
            self.queue_max = int(self.queue_max_batches)

    # Back-compat for older name used internally
    @property
    def queue_max_batches_prop(self) -> int:
        return self.queue_max


class Repo:
    def __init__(self, cfg: RepoConfig):
        self.cfg = cfg
        self.metrics = {
            "dropped_batches": 0,
            "batch_retry_count": 0,
            "write_latency_ms": 0.0,
            "submitted_batches": 0,
        }
        self.q = queue.Queue(maxsize=cfg.queue_max)
        self.stop_flag = False
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.repo = None
        if cfg.backend == "clickhouse":
            from clickhouse_connect import get_client

            host = cfg.clickhouse_url.split("://")[-1].split(":")[0]
            port = int(cfg.clickhouse_url.split(":")[-1]) if ":" in cfg.clickhouse_url else 8123
            self.repo = ("ch", get_client(host=host, port=port))
        elif cfg.backend == "timescale":
            import psycopg

            self.repo = ("ts", psycopg.connect(cfg.timescale_dsn))
            self.repo[1].autocommit = True

    def start(self):
        if not self.thread.is_alive():
            self.thread.start()

    def stop(self):
        # signal loop to exit and join if running
        self.stop_flag = True
        if self.thread.is_alive():
            self.thread.join(timeout=max(2.0, self.cfg.flush_interval_ms / 1000 + 1.0))
        if self.repo and self.repo[0] == "ts":
            try:
                self.repo[1].close()
            except Exception:
                pass

    def submit(self, rows: list[dict]):
        # enforce PK presence
        for r in rows:
            for k in ("run_id", "ts", "symbol", "metric"):
                if k not in r:
                    raise ValueError(f"Missing key {k} in row")
        try:
            self.q.put_nowait(rows)
            self.metrics["submitted_batches"] += 1
        except queue.Full:
            self.metrics["dropped_batches"] += 1

    def _dedupe_rows(self, rows: list[dict]) -> list[dict]:
        """Deduplicate rows by primary key."""
        seen = set()
        out = []
        for r in rows:
            key = (r["run_id"], r["ts"], r["symbol"], r["metric"])
            if key not in seen:
                seen.add(key)
                out.append(r)
        return out

    def _write_clickhouse(self, rows: list[dict]):
        """Write rows to ClickHouse."""
        cols = sorted(rows[0].keys())
        data = [[r.get(c) for c in cols] for r in rows]
        self.repo[1].insert(self.cfg.table, data, column_names=cols)

    def _write_timescale(self, rows: list[dict]):
        """Write rows to TimescaleDB."""
        cols = sorted(rows[0].keys())
        vals = ",".join(["(" + ",".join(["%s"] * len(cols)) + ")"] * len(rows))
        args = []
        for r in rows:
            args.extend([r.get(c) for c in cols])
        cols_sql = ",".join(cols)
        pk_cols = "run_id,ts,symbol,metric"
        sql = (
            f"INSERT INTO {self.cfg.table} ({cols_sql}) VALUES {vals} "
            f"ON CONFLICT ({pk_cols}) DO UPDATE SET "
            + ",".join(
                [f"{c}=EXCLUDED.{c}" for c in cols if c not in ("run_id", "ts", "symbol", "metric")]
            )
        )
        with self.repo[1].cursor() as cur:
            cur.execute(sql, args)

    def _write_rows(self, rows: list[dict]):
        """Write rows to the configured backend."""
        if not self.repo:
            return
        if self.repo[0] == "ch":
            self._write_clickhouse(rows)
        elif self.repo[0] == "ts":
            self._write_timescale(rows)

    def _write_with_retries(self, rows: list[dict], max_attempts: int = 5) -> tuple[bool, int]:
        """Attempt to write with retries and simple backoff. Returns (ok, attempts)."""
        attempts = 0
        while attempts < max_attempts:
            try:
                self._write_rows(rows)
                return True, attempts
            except Exception:
                attempts += 1
                self.metrics["batch_retry_count"] += 1
                # Backoff: 0.2, 0.4, 0.8, 1.0, 1.0
                time.sleep(min(1.0, 0.2 * (2 ** max(0, attempts - 1))))
        return False, attempts

    def _flush(self, rows: list[dict]) -> None:
        """Deduplicate and persist a batch, tracking latency and retries."""
        if not rows:
            return
        out = self._dedupe_rows(rows)
        t0 = time.time()
        ok, attempts = self._write_with_retries(out)
        self.metrics["write_latency_ms"] = (time.time() - t0) * 1000.0
        if not ok:
            self._log_flush_failure(rows, attempts)

    def _log_flush_failure(self, rows: list[dict], attempts: int) -> None:
        """Log flush failure with row count and attempt details."""
        logging.error(
            "failed to flush %d rows after %d attempts", len(rows), attempts, exc_info=True
        )

    def _loop(self):
        buf: list[dict] = []
        last = time.time()
        while not self.stop_flag:
            timeout = max(0.0, self.cfg.flush_interval_ms / 1000 - (time.time() - last))
            try:
                rows = self.q.get(timeout=timeout)
                buf.extend(rows)
                if len(buf) >= self.cfg.batch_size:
                    self._flush(buf)
                    buf = []
                    last = time.time()
            except queue.Empty:
                if buf:
                    self._flush(buf)
                    buf = []
                    last = time.time()

        # Final flush on stop
        try:
            if buf:
                self._flush(buf)
        except Exception as _e:
            logging.warning("final flush error: %s", _e)
