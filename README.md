# HCE Backtest & A/B — v3.3 (All‑in‑One)

**Ημερομηνία:** 2025-10-15

Περιλαμβάνει *όλα* σε ένα πακέτο:
- Shadow fill model (last/mark, bid/ask aware), slippage modes: fixed_ticks, bps, pct_spread, hybrid
- Order types: market, limit (queue/partials), stop, stop-limit
- Deterministic A/B (seed + stable event order)
- Repository abstraction (none|clickhouse|timescale) με batch writer, idempotent upserts, back-pressure
- Docker compose για ClickHouse / Timescale (με DDLs)
- Kahan summation στα reductions + UTC ISO normalizer
- JSON logs, metrics counters, tests (unit/golden + integration smoke)

## Quick start
```bash
pip install -r requirements.txt
# Optional: bring up DBs
docker compose up -d
# Run demo A/B
python backtest.py run --config examples/cfg.yaml --ab examples/A.json examples/B.json
# Run tests
pytest -q
```
