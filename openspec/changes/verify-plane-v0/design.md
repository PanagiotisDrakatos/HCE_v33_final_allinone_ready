## Context

See proposal.md — Why. This design records how the thin slice is built and, because it is a response to an external RFC (GitHub issue #55) plus a prior audit charted in another repository (`claude-golden-setup` wayfinder map #735), which of those proposals are taken now and which are deferred, with the evidence for each.

Constraints that shaped the approach, all measured against `ed24c75`:

- `timescale/timescaledb-ha:pg16-latest` returns 404 on Docker Hub. The current `docker-compose.yml` cannot start. Pinning the image is a prerequisite, not a nicety.
- `examples/A.json` and `examples/B.json` share `ts` and `symbol`; the primary key is `(run_id, ts, symbol, metric)` and `metric` is always `fill_cost`. Two files under one `run_id` therefore collapse to two distinct rows, not four, and the in-buffer dedup keeps the first. A read-back proof must drive fixtures with disjoint `ts`.
- `hcebt/persistence.py` retries a failed write five times (sleeping 0.2+0.4+0.8+1.0+1.0 = 3.4 s) then only logs; `Repo.stop()` joins for 2.0 s. Adding a counter alone leaves a window where `run_ab` returns before the failure is counted.
- The default-branch ruleset (8928787) has no `required_status_checks` rule; CI is not a merge gate today.
- The repo is public, so hosted-runner minutes are unbilled; the cost pressure that blocks the sibling repo does not apply here.

## Goals / Non-Goals

**Goals:**
- One deterministic verification path shared by humans, the pre-push hook, and CI.
- A receipt bound to the source tree, not just the commit, so rebase-identical content stays valid and any file change invalidates it.
- Prove exactly one real feature end to end (Timescale write then read-back) rather than mock it.
- Close the false-green paths the audit and the RFC name, each with a red-first test.

**Non-Goals (design-level boundaries beyond the proposal's scope):**
- No abstraction for a second provider or a second feature until one exists. `scripts/verify.py` is one file, not a package; the name `cif` and a provider interface are reserved for a later cross-project kernel.
- No dependency added to run the kernel: standard library only, so the receipt validator and hashing cannot themselves drift a lockfile.

## Decisions

**D1 — One script, standard library only.** `scripts/verify.py` with subcommands `fast`, `runtime`, `receipt`, `check`, `security`, `clean`. Alternative considered: a `cif/` package with a provider interface (the RFC's shape). Rejected for one repo, one feature, one provider — a single implementation is the lazier correct choice and has nothing to abstract yet.

**D2 — Bind the receipt to `tree_hash`, not the commit.** `git rev-parse HEAD^{tree}` when clean; a temporary-index `git write-tree` when dirty, plus a `diff_hash`. A commit changes on rebase without content changing; the tree does not. Local `check` treats an amend with an identical tree as fresh; the CI aggregate additionally requires the commit to match the merge ref.

**D3 — Compare against the merge-ref tree in CI.** On `pull_request`, both `runtime-verify` and `aggregate` check out the default `github.sha` (the `refs/pull/N/merge` tree) and the aggregate asserts `receipt.tree_hash == git rev-parse HEAD^{tree}`. The receipt also stores `head_sha` for humans; it is never compared against, because it is not the tree that lands. Alternative (checking out `head.sha`) was rejected: it proves a tree that is not what merges.

**D4 — Read back with an independent client.** The runtime proof reads rows with `docker compose exec -T timescaledb psql -tAc`, not through the application's own psycopg path, so a bug in that path cannot mask itself. Assertion: `count(*) == 4 AND count(DISTINCT label) == 2`, driven by `verification/fixtures/{A,B}.json` with disjoint `ts` (fact above).

**D5 — Make the write path honest before gating on it.** Expose `failed_batches` and `unflushed` in `repo_metrics`; `Repo.stop()` joins until the writer loop exits (bounded by the retry budget) and sets `unflushed` if the thread is still alive or the buffer is non-empty; `backtest.py run` exits 2 when any of `failed_batches`, `dropped_batches`, `unflushed` is set.

**D6 — Verdict integrity over check coverage.** Ranks FAIL < INCONCLUSIVE < PASS; aggregate is the minimum. No producer output → INCONCLUSIVE. Zero tests collected or all skipped → INCONCLUSIVE. A missing expected lane or receipt → FAIL. The receipt validator lives in code (~25 lines); `verification/evidence.schema.json` is the published contract and a test asserts the schema's required set matches the validator's.

**D7 — Guards are proven against an attack table, not one planted violation.** Two attack tables (receipt/aggregate, host-global-docker) drive red-first tests; a guard is not accepted until every enumerated bypass is seen to fail. The host-global-docker policy test builds its own violation strings by concatenation so it never flags its own fixtures, and asserts `tests/**` is out of the scanned scope.

### RFC #55 disposition (proposals from the issue body)

| # | RFC proposal | Verdict | Note |
|---|---|---|---|
| 1 | One verification CLI (`cif ...`) | ADD (thin) | `scripts/verify.py`, name `cif` deferred |
| 2 | `verification/` skill + feature map | ADD (thin) | schema + one feature contract + fixtures |
| 3 | Shared baseline + delta runtime | DEFER | no second service; unlock: a networked process |
| 4 | Sandbox identity header | DEFER | no HTTP surface in this repo |
| 5 | Stateful isolation contracts | DEFER | one DB, one project scope suffices |
| 6 | Wayfinder correlation before adding | KEEP | done in this table + the #735 table below |
| 7 | Agent lifecycle hooks | MERGE (partial) | pre-push only; Stop-hook deferred |
| 8 | Evidence receipt | ADD | `.verify/receipt.json`, tree-bound |
| 9 | Docker proof gate | ADD | `up --wait` + health + `down -v` in finally |
| 10 | pre-commit / pre-push split | MERGE | pre-push runs `verify fast`; `prek` deferred |
| 11 | Parallel CI lane graph | ADD | five lanes + aggregate |
| 12 | CI performance work | EXPERIMENT | `uv` installs + cache now; measured in the ledger |
| 13 | Proof levels | KEEP | receipt records per-deliverable level in the PR |
| 14 | Phased sequence A–F | KEEP | this change is A + thin B/C/E |
| 15 | Mandatory reviewer roles | MERGE | `code-review` skill + one adversarial pass on the attack table |

### RFC #55 comment findings (the repository-specific addendum)

| # | Finding | Verdict |
|---|---|---|
| 1 | `make deep-reset` host-global destruction | REMOVE + policy test |
| 2 | Backtests green is not runtime proof | REMOVE placeholder, ADD real proof |
| 3 | `tests`/`pr-guard` serialized on `lint` | MERGE into five independent lanes |
| 4 | Repeated apt/venv/pip bootstrap | EXPERIMENT: `uv` + cache, measured |
| 5 | Compose health under-specified | ADD healthcheck in the overlay |
| 6 | Security `\|\| true` vs block-high | ADD blocking bandit HIGH/HIGH |

### Correlation with wayfinder map #735 (`claude-golden-setup` at `fabdb5ac`)

The audit that produced #735 lives in a sibling repository; these are its findings that touch this work, and how this change relates to each. They are leads carried across a trust boundary, not evidence for this repo; each is re-grounded above.

| #735 finding | Status here | How this change relates |
|---|---|---|
| Evidence receipt schema + atomic lane write (M1 / A4, R4-E-13) | CONFIRMED, adopted thin | This receipt is tree-bound and per-run; atomicity is trivial for one writer, the real lesson (attribution) is deferred with the single-lane design |
| Verdict authority must be able to block (R4-D-01) | CONFIRMED, adopted | The required `aggregate` gate fails on any non-PASS or stale receipt |
| Self-hosted runner unenforceable by labels (R4-D-02, #744) | CONFIRMED, deferred | No self-hosted runner; recorded in the sibling repo's #744 |
| One policy → adapters (M6 / #749) | PARTIAL | One security string shared between `verify.py` and `_project.yaml`; full policy-to-adapter deferred |

## Risks / Trade-offs

- Non-HA Timescale image may run init scripts before `create_hypertable` succeeds on an empty table → the health check waits on `pg_isready` over TCP (not the unix socket the init phase uses), and the read-back preflight treats a missing table as INCONCLUSIVE, so a slow init fails safe rather than false-passing.
- `pip-audit` will likely be red on day one from 12-month-old pins → measured in the Phase A ledger before the gate flips; blocked only on findings with a fix version; never downgraded to `continue-on-error`.
- Every in-repo guard is editable by the PR under review and the ruleset requires zero approvals → these guards close stale, accidental, and fork false-greens; a maintainer editing `verify.py` to print PASS is stopped only by review. CODEOWNERS on `.github/**`, `scripts/verify.py`, `verification/**` is the platform lever, deferred to the operator.
- Docker Hub anonymous rate limits from shared runner IPs could 429 the image pull → no secret is available to fork PRs, so the fallback (a GHCR mirror under the owner) is deferred until observed.

## Migration Plan

Ten small commits on `agent/verify-plane-v0`, red-first (policy and receipt tests before the kernel). Rollback is per-commit; the receipt and `.verify/` are gitignored. The required `aggregate` context is added to the ruleset only after merge, because open Dependabot PRs still carry the old workflow and would otherwise block on an "Expected" check.

## Open Questions

None that change the spec, approach, or task breakdown. The image pull time and the non-HA init timing are measured, not designed, and are recorded in the Phase A ledger.
