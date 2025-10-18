## Summary
- Linux/Bash/WSL-only
- Ruff-only (lint/format/imports)
- CI: ubuntu-latest with pip & ruff cache
- PR Guard: clean merge, behind-base check, no merge-commits, forbid Windows scripts, Conventional title

## Checks
- [ ] `ruff format --check .`
- [ ] `ruff check .`
- [ ] `pytest -q`
