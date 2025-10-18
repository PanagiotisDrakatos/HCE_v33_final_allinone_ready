chore(ci): Linux/WSL-only + Ruff-only + act-friendly CI

- Remove Windows/cmd/PowerShell scripts & references.
- Switch to **Ruff-only** (lint/format/imports) across CLI, hooks, CI, docs.
- Simplify CI to **ubuntu-latest** with ruff + pytest; pip & ruff caching.
- Add **PR Guard** (clean merge, behind-base check, no merge-commits, forbid Windows scripts, Conventional PR title).
- Rework **Makefile** & **quick_pr.sh** (Bash-only, env-aware, act auto-install/fallback).

Local verification:
```bash
make ci-local
RUN_BACKTESTS=0 make pr
```
