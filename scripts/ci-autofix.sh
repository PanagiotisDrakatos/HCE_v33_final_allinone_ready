#!/usr/bin/env bash
set -euo pipefail
if ! command -v ruff >/dev/null 2>&1; then
  python -m pip install --upgrade pip
  pip install ruff
fi
echo "==> Ruff --fix"
ruff check . --fix || true
echo "==> Ruff format"
ruff format . || true
echo "Autofix run complete."
