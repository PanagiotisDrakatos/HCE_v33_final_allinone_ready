chore(ci): Linux/WSL-only + Ruff-only + act-friendly CI

This PR applies the Linux/Ruff automation pack to streamline CI and local validation.

What changed
- Workflows: removed legacy ones; kept only .github/workflows/ci.yml and codeql.yml
- CI: Ubuntu-only runners, Ruff-only lint; optional integration job via services
- Pre-commit: Ruff lint/format hooks only
- Makefile: Ruff-only targets and `make pr` for quick PR flow
- Hooks: pre-push enforces Ruff + pytest gates; post-commit attempts push
- Scripts: added quick_pr.sh; aligned helpers to Ruff-only (no Black/isort/flake8)
- Tooling: act-friendly defaults to let you dry-run CI locally

Why
- Reduce matrix flakiness and maintenance
- One linter (Ruff) for speed and simplicity
- Make it easy to preview CI locally with `act`

How to try locally (optional)
- Windows (cmd):
  set AUTO_INSTALL_ACT=1 && set RUN_BACKTESTS=0 && make pr
- WSL/Linux/macOS:
  AUTO_INSTALL_ACT=1 RUN_BACKTESTS=0 make pr

Notes
- No functional changes to the backtest engine
- Integration tests run only on demand in CI or if services are available locally

