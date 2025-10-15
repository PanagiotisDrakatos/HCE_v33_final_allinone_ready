#!/usr/bin/env bash
set -euo pipefail
echo "==> Unit tests with coverage gate"
pytest -q
echo "==> Integration tests (if DBs enabled)"
pytest -q -m integration || true
echo "==> Lint & format"
ruff check .
black --check .
echo "==> Security audit (pip-audit) [non-blocking]"
pip-audit -r requirements.txt || true
echo "==> Secret scan (TruffleHog) [non-blocking]"
trufflehog filesystem --no-update --only-verified . || true
echo "All checks done."
