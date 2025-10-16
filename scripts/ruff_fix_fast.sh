#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "⚡ Ruff Fast Format"

RUFF_VERSION="0.5.7"
VENV_DIR=".venv_ruff"
RUFF_BIN="ruff"

# --- ensure Ruff installed (prefer system, else local venv) ---
if ! command -v ruff &>/dev/null; then
  if [[ ! -x "${VENV_DIR}/bin/ruff" ]]; then
    echo "🚀 Setting up local Ruff venv at ${VENV_DIR} ..."
    python3 -m venv "${VENV_DIR}"
    "${VENV_DIR}/bin/python" -m pip install --disable-pip-version-check --no-input "ruff==${RUFF_VERSION}" >/dev/null
  fi
  RUFF_BIN="${VENV_DIR}/bin/ruff"
fi

# --- run Ruff format ---
echo "🔍 Running: ${RUFF_BIN} format -q ."
"${RUFF_BIN}" format -q .

echo "✅ Ruff format complete."
