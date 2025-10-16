#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# 0) Install uv if missing (fast installer for ruff)
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

# 1) Determine Ruff version from requirements-dev.txt if available; fallback to a stable pin
RUFF_VERSION="${RUFF_VERSION:-}"
if [ -z "${RUFF_VERSION:-}" ] && [ -f requirements-dev.txt ]; then
  # Extract first version-ish token after 'ruff'
  RUFF_VERSION="$(grep -iE '^\s*ruff(\s*[=~<>!]{1,2}\s*[^#[:space:]]+)?' requirements-dev.txt | head -n1 | sed -E 's/.*ruff[^0-9]*([0-9][^[:space:]]*).*/\1/' || true)"
fi
if [ -z "${RUFF_VERSION:-}" ] || ! echo "$RUFF_VERSION" | grep -Eq '^[0-9]'; then
  RUFF_VERSION="0.6.9"
fi

# 2) Create or reuse cached venv dedicated to ruff
VENV_DIR=".venv-ruff-${RUFF_VERSION}"
if [ ! -d "$VENV_DIR" ]; then
  uv venv "$VENV_DIR"
  . "$VENV_DIR/bin/activate"
  if ! uv pip install "ruff==${RUFF_VERSION}"; then
    # Fallback: install latest available ruff
    uv pip install ruff
  fi
else
  . "$VENV_DIR/bin/activate"
fi

# 3) Compute base commit for diff
BASE="$(git merge-base HEAD origin/main 2>/dev/null || git merge-base HEAD main 2>/dev/null || echo HEAD~1)"

# 4) Collect changed Python files (NUL-delimited), filter out deleted paths, and run Ruff
#    Use a temp file to safely hold NUL bytes.
TMP_LIST="$(mktemp)"
trap 'rm -f "$TMP_LIST"' EXIT

git -c core.quotepath=false diff --name-only -z --diff-filter=d "$BASE"...HEAD -- "*.py" >"$TMP_LIST" || true

# Read NUL-delimited file list into an array safely
mapfile -d '' -t CHANGED_FILES <"$TMP_LIST" || true

RUFF_ARGS=(check --force-exclude)
if [ "${RUFF_CHECK:-0}" -eq 0 ]; then
  RUFF_ARGS+=(--fix)
fi

if [ ${#CHANGED_FILES[@]} -gt 0 ]; then
  echo "🔍 Ruff on changed files (${#CHANGED_FILES[@]})…"
  ruff "${RUFF_ARGS[@]}" -- "${CHANGED_FILES[@]}"
else
  echo "🔍 Ruff on all files…"
  ruff "${RUFF_ARGS[@]}" .
fi

echo "✅ Ruff completed"
