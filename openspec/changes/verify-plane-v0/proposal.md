## Why

Today a green CI run does not prove the backtest engine actually persists anything. The `backtests` job echoes a placeholder string, `hcebt/persistence.py` swallows every write failure after five retries and only logs, and the two integration "round-trip" tests are `assert True`. A change can pass every gate while the database write path is broken. This change adds a runtime proof — launch the real TimescaleDB, drive the CLI, read the rows back — bound to the exact source tree by a content-addressed receipt, so an agent or a human can tell a real pass from a plausible one. It implements the thin, provider-neutral slice of RFC #55 (Phases A, B, and the CI parts of E), without sandbox routing, Kubernetes, Signadot, or a self-hosted runner.

## What Changes

- Add `scripts/verify.py` (standard library only): subcommands `fast`, `runtime`, `receipt`, `check`, `security`, `clean`. One deterministic path that humans, hooks, and CI all call.
- Add a **content-addressed evidence receipt** at `.verify/receipt.json` bound to `tree_hash` (not just the commit): a stale receipt cannot make a new change green. `verify check` recomputes the tree hash and inputs digest and refuses a mismatch.
- Add a **runtime proof** for one real feature: bring up TimescaleDB via a `compose.verify.yml` overlay with a health check, run `backtest.py`, and read the rows back with an independent `psql` query. Watching stdout is not enough because the writer hides failures.
- Make the write path honest: expose `failed_batches` and `unflushed` in `repo_metrics` and make `backtest.py run` exit non-zero when a batch was lost. **BREAKING** for callers that relied on exit 0 after a silent write failure.
- **Remove** `make deep-reset` (host-global `docker system prune -af --volumes` and `docker rm -f $(docker ps -aq)`), replace it with a project-scoped `make clean-runtime`, and add a policy test that rejects host-global Docker commands from the tracked tree.
- Make the security gate blocking: `bandit` at HIGH severity and HIGH confidence, `pip-audit` when a fix version exists; drop the `|| true` on the Python security command.
- Rebuild CI into five independent lanes (`static`, `unit`, `pr-policy`, `security`, `runtime-verify`) plus a single required `aggregate` gate that validates the receipt against the merge-ref tree. SHA-pin every action.
- Fix test defects: mark the real integration tests `integration`, turn the two `assert True` placeholders into real read-back tests, give the empty `tests/test_config_validation.py` one real test.
- Remove the orphaned `tmp/` gitlink (mode 160000, empty `.gitmodules`) from the index.
- Pin the Timescale image: `timescale/timescaledb-ha:pg16-latest` no longer exists on Docker Hub.

## Capabilities

### New Capabilities

- `verify-plane`: a deterministic verification interface that produces a content-addressed evidence receipt, proves one real runtime feature against live dependencies, and is enforced by a single required CI aggregate gate.

### Modified Capabilities

None. No existing capability spec is defined in `openspec/specs/`; the behavior added here is new.

## Impact

- New: `scripts/verify.py`, `compose.verify.yml`, `verification/` (schema, feature contract, fixtures, Phase A ledger), `tests/policy/`, `tests/verify/`.
- Modified: `docker-compose.yml`, `Makefile`, `hooks/pre-push`, `hcebt/persistence.py`, `hcebt/runner.py`, `backtest.py`, `.prompts/_project.yaml`, `requirements-dev.txt`, `pytest.ini` markers, `.github/workflows/ci.yml`, `.github/workflows/codeql.yml`, `.gitignore`.
- Removed: `make deep-reset`, the `tmp/` gitlink, the placeholder `backtests` job.
- Operator handbacks (outside the PR): re-enable the inactive CodeQL workflow, add `aggregate` as a required status check to ruleset 8928787 after merge, install the Docker Compose v2 plugin locally.
- Deferred (RFC #55, not this change): sandbox identity / request routing, delta-service runtime, Stop-hook receipt gate, image-digest guard, ClickHouse proof, `prek`, `uv.lock`, Proxmox / self-hosted runner.
