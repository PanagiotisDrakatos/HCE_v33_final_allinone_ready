#!/usr/bin/env bash
set -euo pipefail
echo "==> Unit tests"
if command -v pytest >/dev/null 2>&1; then
  pytest -q
else
  echo "pytest not found — skipping"
fi
echo "==> Lint & format (ruff-only)"
ruff check .
ruff format --check .
echo "All checks done."
