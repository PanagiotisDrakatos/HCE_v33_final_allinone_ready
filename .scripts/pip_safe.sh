#!/usr/bin/env bash
set -euo pipefail

# Safe wrapper around pip to handle PEP 668 automatically.
# Example:
#   .scripts/pip_safe.sh install -r requirements-dev.txt

try_pip() {
  python3 -m pip "$@" 2>/dev/null
}

if try_pip "$@"; then
  exit 0
fi

echo "⚠️  PEP 668 detected (externally-managed). Falling back to repo venv..."

VENV_DIR="${VENV_DIR:-.git/tools-venv}"
if [ ! -d "${VENV_DIR}" ]; then
  command -v python3 >/dev/null 2>&1 || { echo "python3 not found"; exit 1; }
  python3 -m venv "${VENV_DIR}"
  "${VENV_DIR}/bin/python" -m pip install -U pip wheel >/dev/null 2>&1
fi

"${VENV_DIR}/bin/python" -m pip "$@"

echo "✅ Installed via repo venv at ${VENV_DIR}"

