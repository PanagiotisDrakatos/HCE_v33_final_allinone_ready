## 1. Baseline and cleanup

- [ ] 1.1 Add `verification/PHASE_A_LEDGER.md` with the December 2025 CI datapoint, the `pg16-latest` 404, and the baseline `bandit`/`pip-audit` counts; verify the file lists a measured number for each and links the run id.
- [ ] 1.2 Remove the orphaned `tmp/` gitlink (`git rm --cached tmp`), delete the empty `.gitmodules`, add `tmp/`, `.verify/`, `graphify-out/` to `.gitignore`; verify `git ls-files tmp` is empty and `git status` is clean.

## 2. Red-first tests (must fail on origin/main)

- [ ] 2.1 Add `tests/policy/test_no_host_global_docker.py` with the 16-row attack table; verify it is RED against `origin/main` on `Makefile` `deep-reset`.
- [ ] 2.2 Add `tests/policy/test_ci_policy.py` (no `aggregate`, `--cov=.` in ci.yml, `|| true` in `_project.yaml`, missing integration marker, two `assert True`, `.verify/` not tracked, no `continue-on-error`, overlay healthcheck without fixed port/container_name); verify RED against `origin/main`.
- [ ] 2.3 Add `tests/test_persistence_failed_batches.py` and `tests/test_backtest_cli_exit.py`; verify RED (keys absent, exit 0 today).
- [ ] 2.4 Add `tests/verify/` (`test_receipt.py`, `test_check.py`, `test_verdict.py`, `test_schema.py`, `test_runtime_parsers.py`, `test_runtime.py`) covering the receipt/aggregate attack table with a fake subprocess seam; verify RED by absence of `scripts/verify.py`.
- [ ] 2.5 Run the one red command in design D7 against a pristine `origin/main` worktree with `addopts` cleared; verify every listed test is RED and `exit=1`.

## 3. Kernel and honest write path

- [ ] 3.1 Implement `scripts/verify.py` (`fast`, `receipt`, `check`, `security`, `clean`; stdlib only, under 500 lines) with the code-side validator; verify the §2 non-runtime tests go GREEN.
- [ ] 3.2 Add `failed_batches`/`unflushed` to `hcebt/persistence.py` and make `backtest.py run` exit 2 on any lost batch; verify `test_persistence_failed_batches.py` and `test_backtest_cli_exit.py` pass.
- [ ] 3.3 Fix test defects: mark the real integration tests `integration`, turn the two placeholders into read-back tests, give `tests/test_config_validation.py` one real test; verify `pytest -m "not integration"` passes and coverage holds at 85%.
- [ ] 3.4 Make the security gate blocking (bandit HIGH/HIGH, pip-audit fix-only), add `bandit` to `requirements-dev.txt`, align `.prompts/_project.yaml`; verify `verify security` exits non-zero only on a HIGH/HIGH finding or a fixable CVE.
- [ ] 3.5 Delete `make deep-reset`, add `make verify`, `make verify-check`, `make clean-runtime`; verify `make deep-reset` reports "No rule to make target" and the policy test passes.

## 4. Runtime provider

- [ ] 4.1 Pin the Timescale image in `docker-compose.yml`, drop the obsolete `version:` key, add `compose.verify.yml` (unique project, ephemeral port, `pg_isready` healthcheck); verify `test_ci_policy.py` overlay assertions pass.
- [ ] 4.2 Add `verification/features/backtest-timescale.md`, `verification/fixtures/{A,B}.json` (disjoint `ts`), `verification/evidence.schema.json`; verify `test_schema.py` binds schema to validator.
- [ ] 4.3 Implement `verify runtime` (compose up `--wait`, backtest, independent read-back `== 4 / DISTINCT label == 2`, timing fields, teardown in finally, exclusive lock); verify `make verify` writes a PASS receipt whose `tree_hash` equals `git rev-parse HEAD^{tree}` (requires the Docker Compose v2 plugin — operator handback).
- [ ] 4.4 Update `hooks/pre-push` (and its duplicate) to run `verify fast` + `receipt`, runtime only under `VERIFY_RUNTIME=1`; verify a push with a failing gate is blocked and a clean one is not.

## 5. CI and close-out

- [ ] 5.1 SHA-pin every action in `ci.yml` and `codeql.yml` with `# vX.Y.Z` comments; verify each ref resolves (`gh api .../git/ref/tags`).
- [ ] 5.2 Replace the serial graph with five lanes + `aggregate` (required, `if: always()`, explicit `needs.*.result`, receipt download + `verify check` against the merge-ref tree, no secrets); verify a draft PR shows six checks and the aggregate is red when any lane is.
- [ ] 5.3 Record after-measurements in the Phase A ledger and open the PR with `Refs #55`; verify the DONE block in the plan runs clean (receipt PASS, stale-receipt exit 1, no leftover `hce-verify-*` project, `make deep-reset` gone, policy test red when re-added).
