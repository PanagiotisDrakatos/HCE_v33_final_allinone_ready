# Feature: backtest → TimescaleDB round-trip

Feature id: `timescale-roundtrip`. This is the one real feature the verify plane
proves. It is DRAFT until `verify runtime` has produced a PASS receipt for it.

- **Launch** — `docker compose -f docker-compose.yml -f compose.verify.yml -p hce-verify-<tree>-<nonce> up -d --wait --wait-timeout 120 timescaledb`. Ephemeral host port, project-prefixed name, so parallel runs do not collide.
- **Doctor** — the compose health check (`pg_isready -h 127.0.0.1 -U postgres -d hce`) must report `healthy` before driving. An empty or `starting` health is INCONCLUSIVE, never a pass. A missing `market_signals` table (`to_regclass` is null) is INCONCLUSIVE.
- **Drive** — `python backtest.py run --config <generated> --ab verification/fixtures/A.json verification/fixtures/B.json` with `backend: timescale` and a unique `run_id`. Fixtures use disjoint `ts` so the two files write four distinct primary keys, not two (the PK is `(run_id, ts, symbol, metric)`).
- **Observe** — read back with an independent client: `psql -tAc "SELECT count(*), count(DISTINCT label) FROM market_signals WHERE run_id=..."`. Proof is `4` rows and `2` labels. Watching the CLI's stdout is not enough: the writer retries then only logs, so a total write failure still prints a clean result.
- **Cleanup** — `docker compose ... down -v --remove-orphans` in a `finally` block (also on failure and on SIGTERM); remove the generated config and any `run_artifacts/<run_id>`. Never a host-global prune.
- **Evidence** — `.verify/receipt.json`: `runtime.pull_ms`, `runtime.up_wait_ms`, `container_health`, the `runtime-timescale` check with `rows`/`labels`, and `timescale-roundtrip` appended to `features_verified` only after the read-back matches.
