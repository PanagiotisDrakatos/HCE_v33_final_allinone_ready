#!/usr/bin/env bash
set -euo pipefail

# Repo-local tooling venv to avoid PEP 668 (externally-managed)
# Usage: source/execute this before any host-side pip installs

VENV_DIR="${VENV_DIR:-.git/tools-venv}"

if [ ! -d "${VENV_DIR}" ]; then
  command -v python3 >/dev/null 2>&1 || { echo "python3 not found"; exit 1; }
  echo "📦 Creating tooling venv at ${VENV_DIR}..."
  python3 -m venv "${VENV_DIR}"
  "${VENV_DIR}/bin/python" -m pip install -U pip wheel >/dev/null 2>&1
fi

echo "✅ Tooling venv ready at ${VENV_DIR}"
echo "💡 To use: source ${VENV_DIR}/bin/activate"

