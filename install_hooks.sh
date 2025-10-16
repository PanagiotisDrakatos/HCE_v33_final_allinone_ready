#!/usr/bin/env bash
# Installs git hooks into the current repository.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "${ROOT}" ]]; then
  echo "Run this script from inside a git repository." >&2
  exit 1
fi

echo "[install] Repo root: $ROOT"
mkdir -p "$ROOT/.git/hooks"

cp -f "./hooks/pre-push" "$ROOT/.git/hooks/pre-push"
cp -f "./hooks/post-commit" "$ROOT/.git/hooks/post-commit"
chmod +x "$ROOT/.git/hooks/pre-push" "$ROOT/.git/hooks/post-commit"

echo "[install] Installed hooks:"
ls -l "$ROOT/.git/hooks/pre-push" "$ROOT/.git/hooks/post-commit"
echo "[install] Done ✅"
