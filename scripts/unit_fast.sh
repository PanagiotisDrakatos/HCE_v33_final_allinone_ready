#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

VENV_DIR="$(ls -dt .venv-* 2>/dev/null | head -n1 || true)"
if [ -z "${VENV_DIR:-}" ]; then
  echo "❌ No venv found. Run scripts/bootstrap.sh first."
  exit 1
fi
. "$VENV_DIR/bin/activate"

# Keep pytest clean and deterministic
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1

# Determine a base commit to compare for changed files
BASE="$(git merge-base HEAD origin/main 2>/dev/null || true)"
if [ -z "$BASE" ]; then BASE="HEAD~1"; fi
CHANGED="$(git diff --name-only "$BASE"...HEAD | grep -E '\.py$' || true)"

if [ -n "$CHANGED" ]; then
  echo "🔍 Linting changed files..."
  echo "$CHANGED" | tr '\n' ' ' | xargs -r ruff check --select I,E,F,UP
  echo "$CHANGED" | tr '\n' ' ' | xargs -r black --check
else
  ruff check --select I,E,F,UP .
  black --check .
fi

echo "⚙️  Running fast unit tests..."
pytest -q -m "not integration" -n auto --cov=hcebt --cov=lib --cov-report=xml

