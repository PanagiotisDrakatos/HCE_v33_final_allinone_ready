# Phase A ledger — verify-plane-v0

Read-only measurements taken before any behaviour change, plus the fresh
baseline captured on this PR's first CI run. Numbers are evidence, not targets;
the RFC's `<=60 s` figure is a target only and is not claimed here. Phase F
appends measured before/after with p50/p95 when it exists.

## Historical CI datapoint (last run before this change)

Run `19812372282`, workflow `ci.yml`, 2025-12-01 (a Dependabot PR, all green).
Step-level timings expired (90-day retention); job and wall times survive.

| Job | Duration | Conclusion |
|---|---:|---|
| Ruff Lint & Format (check) | 25 s | success |
| Unit Tests | 50 s | success |
| PR Guard (merge/conflicts/policy) | 22 s | success |
| Backtests (optional) | 45 s | success |
| Run wall (serial: lint -> {tests, pr-guard}; tests -> backtests) | 130 s | — |

Runner image version at that time is unknown. This is one datapoint, not a
distribution.

## Findings that shaped the change (measured 2026-09-21 against `ed24c75`)

- **`timescale/timescaledb-ha:pg16-latest` is gone.** Docker Hub returns 404 for
  that tag (two API calls). The committed `docker-compose.yml` cannot start.
  Pinned to `timescale/timescaledb:2.30.1-pg16@sha256:f495f2bc25ca7596ca8e1606c6241ca250ccc56a0c082b9f2ec0d290e0126cd9`
  (non-HA is enough: `init.sql` only runs `CREATE EXTENSION timescaledb`).
- **A+B under one run_id yields 2 rows, not 4.** `examples/A.json` and
  `examples/B.json` share `ts` and `symbol`; the primary key is
  `(run_id, ts, symbol, metric)` and `metric` is always `fill_cost`. The runtime
  proof drives `verification/fixtures/{A,B}.json` with disjoint `ts` and asserts
  `count(*) == 4 AND count(DISTINCT label) == 2`. The schema losing A-vs-B on a
  collision is a real product defect, filed separately (out of scope here).
- **Silent write failures.** `hcebt/persistence.py` retried a failed write five
  times then only logged. Now `failed_batches`/`unflushed` are surfaced and
  `backtest.py run` exits 2 on any lost batch.
- **Security baseline.**
  - bandit HIGH severity + HIGH confidence over `hcebt lib backtest.py`: **0**.
  - pip-audit fixable vulnerabilities on the committed pins: **click 8.1.7 ->
    8.3.3 (PYSEC-2026-2132)** and **pytest 8.3.2 -> 9.0.3 (PYSEC-2026-1845)**.
    click (runtime) is bumped to its fix version. The pytest advisory is a
    dev/test-only tool and a major bump that also needs a pytest-cov upgrade;
    it is dated-ignored in `verification/pip-audit-ignore.txt` (review 2026-12-21),
    never with `|| true` or `continue-on-error`.
- **Unit suite (local, `pytest -m "not integration"`):** 115 passed, coverage
  90.10% (gate 85%).
- **Kernel, Docker-free (local):** `verify fast` PASS; `verify receipt` PASS;
  `verify check` ok; editing a source file makes `verify check` exit 1 with
  "stale receipt: tree changed".

## Fresh baseline (old ci.yml, this PR's first draft run)

Captured with:

```bash
R=PanagiotisDrakatos/HCE_v33_final_allinone_ready
gh api "repos/$R/actions/runs/<id>/attempts/<n>/jobs" \
  --jq '.jobs[] | {name, queue: ((.started_at|fromdate)-(.created_at|fromdate)), secs: ((.completed_at|fromdate)-(.started_at|fromdate))}'
```

| Attempt | Cache | lint | tests | pr-guard | backtests | wall |
|---|---|---:|---:|---:|---:|---:|
| 1 (cold) | _pending_ | | | | | |
| 2 (warm) | _pending_ | | | | | |
| 3 (warm) | _pending_ | | | | | |

## After (new five-lane graph, final commit)

| Attempt | Cache | static | unit | pr-policy | security | runtime-verify | aggregate | critical path |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 1 (cold) | _pending_ | | | | | | | |
| 2 (warm) | _pending_ | | | | | | | |
| 3 (warm) | _pending_ | | | | | | | |

`runtime.pull_ms` and `runtime.up_wait_ms` for the pinned Timescale image are
read from the receipt of each runtime-verify run.
