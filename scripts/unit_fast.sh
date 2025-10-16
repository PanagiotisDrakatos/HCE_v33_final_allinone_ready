#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

VENV_DIR="$(ls -dt .venv-* 2>/dev/null | head -n1 || true)"
if [ -z "${VENV_DIR:-}" ]; then
  echo "❌ No venv found. Run scripts/bootstrap.sh first."
  exit 1
fi
. "$VENV_DIR/bin/activate"

# Only Ruff linting
echo "🔍 Linting (ruff)..."
ruff check --select I,E,F,UP .
