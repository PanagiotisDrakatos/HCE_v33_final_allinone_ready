#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Ensure uv is installed and available on PATH
if ! command -v uv >/dev/null 2>&1; then
  echo "Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

# Determine Ruff version from requirements-dev.txt if available; fallback to a stable pin
RUFF_VERSION="${RUFF_VERSION:-}"
if [ -z "${RUFF_VERSION:-}" ] && [ -f requirements-dev.txt ]; then
  # Extract version token after 'ruff' on its line
  RUFF_VERSION="$(grep -iE '^\s*ruff(\s*[=~<>!]{1,2}\s*[^#[:space:]]+)?' requirements-dev.txt | head -n1 | sed -E 's/.*ruff[^0-9]*([0-9][^[:space:]]*).*/\1/' || true)"
fi
if [ -z "${RUFF_VERSION:-}" ] || ! echo "$RUFF_VERSION" | grep -Eq '^[0-9]'; then
  RUFF_VERSION="0.6.9"
fi
VENV_DIR=".venv-ruff-${RUFF_VERSION}"

# Create or reuse the venv and install Ruff only via uv (cached)
if [ ! -d "$VENV_DIR" ]; then
  echo "Creating venv: $VENV_DIR"
  uv venv "$VENV_DIR"
  . "$VENV_DIR/bin/activate"
  if ! uv pip install "ruff==${RUFF_VERSION}"; then
    uv pip install ruff
  fi
else
  . "$VENV_DIR/bin/activate"
fi

# Ensure pip tooling is present (quiet best-effort)
python -m pip install -q --upgrade pip wheel >/dev/null 2>&1 || true

echo "✅ Bootstrapped env (ruff-only): $VENV_DIR"
