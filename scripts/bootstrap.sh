#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# Ensure uv is installed and available on PATH
if ! command -v uv >/dev/null 2>&1; then
  echo "Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

# Compute a stable hash from combined requirements to key the venv
REQ_HASH="$(cat requirements.txt requirements-dev.txt 2>/dev/null | sha256sum | awk '{print $1}')"
if [ -z "${REQ_HASH:-}" ]; then
  REQ_HASH="$(date +%s)"
fi
VENV_DIR=".venv-${REQ_HASH}"

# Create or reuse the venv and install deps via uv (cached)
if [ ! -d "$VENV_DIR" ]; then
  echo "Creating venv: $VENV_DIR"
  uv venv "$VENV_DIR"
  . "$VENV_DIR/bin/activate"
  # Try combined install first, then fall back to individual files if needed
  if [ -f requirements.txt ] || [ -f requirements-dev.txt ]; then
    uv pip install -r requirements.txt -r requirements-dev.txt || true
    [ -f requirements.txt ] && uv pip install -r requirements.txt || true
    [ -f requirements-dev.txt ] && uv pip install -r requirements-dev.txt || true
  fi
else
  . "$VENV_DIR/bin/activate"
fi

# Helpful dev tools for fast local runs
python -m pip install -q --upgrade pip wheel >/dev/null 2>&1 || true
pip install -q pytest pytest-xdist ruff black >/dev/null 2>&1 || true

# Keep pytest clean and deterministic
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1

echo "✅ Bootstrapped fast env: $VENV_DIR"

