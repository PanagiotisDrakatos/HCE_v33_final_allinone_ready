#!/usr/bin/env bash
set -euo pipefail
branch="$(git rev-parse --abbrev-ref HEAD)"
run_id="$(gh run list -b "$branch" --json databaseId,conclusion,status,name,headBranch \
  -q '[.[] | select(.status=="completed")][0].databaseId')"
if [[ -z "${run_id:-}" ]]; then
  echo "No completed runs for branch $branch"; exit 1
fi
mkdir -p .ci
gh run view "$run_id" --log > .ci/last_ci.log
echo "[saved] .ci/last_ci.log"
