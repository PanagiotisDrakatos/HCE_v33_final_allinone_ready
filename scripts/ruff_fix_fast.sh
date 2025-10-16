#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "⚡ Ruff Fast Fix (cached <0.5s)"

RUFF_VERSION="0.5.7"
VENV_DIR=".venv_ruff"
RUFF_BIN="ruff"
RUFF_CACHE=".ruff_cache"

# 1) Find ruff or set up lightweight local venv just for ruff
if command -v ruff >/dev/null 2>&1; then
  RUFF_BIN="ruff"
else
  if [[ ! -x "${VENV_DIR}/bin/ruff" ]]; then
    echo "🚀 Installing Ruff ${RUFF_VERSION} into ${VENV_DIR} ..."
    python3 -m venv "${VENV_DIR}"
    "${VENV_DIR}/bin/python" -m pip install --disable-pip-version-check --no-input "ruff==${RUFF_VERSION}" >/dev/null
  fi
  RUFF_BIN="${VENV_DIR}/bin/ruff"
fi

# 2) Lint + auto-fix (don’t block on remaining violations)
echo "🔧 ${RUFF_BIN} check --fix (cache: ${RUFF_CACHE})"
set +e
"${RUFF_BIN}" check --fix --force-exclude --cache-dir "${RUFF_CACHE}" --quiet .
CHECK_RC=$?
set -e

# 3) Formatter (Black-compatible) — always safe
echo "🧹 ${RUFF_BIN} format"
"${RUFF_BIN}" format --quiet .

# 4) Don’t hang on non-zero from check
if [ $CHECK_RC -ne 0 ]; then
  echo "⚠️  Ruff fixed what it could; remaining issues are reported but won't block."
fi

echo "✅ Done."
