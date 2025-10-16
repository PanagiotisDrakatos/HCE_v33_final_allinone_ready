#!/usr/bin/env bash
set -euo pipefail

python -V || true

# Ensure tools are present
if ! command -v ruff >/dev/null 2>&1; then
  python -m pip install --upgrade pip
  pip install ruff
fi
if ! command -v black >/dev/null 2>&1; then
  python -m pip install --upgrade pip
  pip install black
fi

echo "==> Ruff --fix"
ruff check . --fix || true

echo "==> Black format"
black . || true

# Show resulting diff for CI logs
if git rev-parse --git-dir >/dev/null 2>&1; then
  echo "==> Git status after autofix"
  git status --porcelain || true
fi

echo "Autofix run complete."
