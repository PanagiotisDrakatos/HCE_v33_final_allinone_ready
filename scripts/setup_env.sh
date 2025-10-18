#!/usr/bin/env bash
set -euo pipefail
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip wheel
[ -f requirements.txt ] && pip install -r requirements.txt || true
[ -f requirements-dev.txt ] && pip install -r requirements-dev.txt || true
echo "✅ Virtualenv ready at .venv (Linux/WSL only)."
