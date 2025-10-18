#!/usr/bin/env bash
set -euo pipefail

# Quick PR helper
# - optionally installs `act` (if AUTO_INSTALL_ACT=1)
# - runs CI locally with act (Linux-only image)
# - pushes the branch and opens a PR with gh using PR_BODY.md
# - optionally applies labels via LABELS env (comma or space separated)

BRANCH_NAME=${BRANCH_NAME:-chore/ci-linux-ruff-act}
PR_TITLE=${PR_TITLE:-"chore(ci): Linux/WSL-only + Ruff-only + act-friendly CI"}
BASE_BRANCH=${BASE_BRANCH:-main}
ACT_IMAGE=${ACT_PLATFORM:-"ubuntu-latest=ghcr.io/catthehacker/ubuntu:act-24.04"}
RUN_BACKTESTS=${RUN_BACKTESTS:-1}
RUN_ACT=${RUN_ACT:-1}
RUN_ACT_BEFORE_PUSH=${RUN_ACT_BEFORE_PUSH:-1}
AUTO_INSTALL_ACT=${AUTO_INSTALL_ACT:-0}
LABELS=${LABELS:-}

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

echo "[quick_pr] Repo: $ROOT"

ensure_bin() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "[quick_pr] Missing $1; attempting local install..."
    case "$1" in
      act)
        mkdir -p .bin
        if command -v curl >/dev/null 2>&1 && command -v tar >/dev/null 2>&1; then
          url=${ACT_URL:-"https://github.com/nektos/act/releases/download/v0.2.61/act_Linux_x86_64.tar.gz"}
          echo "[quick_pr] Downloading act from: $url"
          (cd .bin && curl -fsSL "$url" -o act.tgz && tar -xzf act.tgz && rm -f act.tgz) || true
          if [[ -f .bin/act ]]; then chmod +x .bin/act; export PATH="$PWD/.bin:$PATH"; fi
        fi
        ;;
      gh)
        echo "[quick_pr] gh is not installed; PR creation will be skipped."
        ;;
    esac
  fi
}

if [[ "$AUTO_INSTALL_ACT" == "1" ]]; then
  ensure_bin act
fi

# Create/switch branch
current_branch="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$current_branch" != "$BRANCH_NAME" ]]; then
  echo "[quick_pr] Switching to branch: $BRANCH_NAME"
  git checkout -B "$BRANCH_NAME"
fi

# Ensure we have a commit; if there are staged/unstaged changes, commit with default message
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "[quick_pr] Committing pending changes"
  git add -A
  git commit -m "chore(ci): apply Linux/Ruff automation pack"
fi

# Optional: run act before pushing
if [[ "$RUN_ACT" == "1" && "$RUN_ACT_BEFORE_PUSH" == "1" ]]; then
  if command -v act >/dev/null 2>&1; then
    echo "[quick_pr] Running act for lint_and_unit job"
    act -j lint_and_unit -W .github/workflows/ci.yml -P "$ACT_IMAGE" || true
    if [[ "$RUN_BACKTESTS" == "1" ]]; then
      echo "[quick_pr] Running act for integration job"
      act -j integration -W .github/workflows/ci.yml -P "$ACT_IMAGE" || true
    fi
  else
    echo "[quick_pr] act not available; skipping local CI run."
  fi
fi

# Push branch
echo "[quick_pr] Pushing branch to origin"
if ! git push -u origin "$BRANCH_NAME"; then
  echo "[quick_pr] Push failed. Ensure you have write access and are authenticated."
  exit 1
fi

# Prepare labels args
LABEL_ARGS=()
if [[ -n "$LABELS" ]]; then
  # support comma or space separated
  IFS=',' read -ra PARTS <<< "${LABELS// /,}"
  for lb in "${PARTS[@]}"; do
    [[ -n "$lb" ]] && LABEL_ARGS+=( -l "$lb" )
  done
fi

# Open PR with gh if available
if command -v gh >/dev/null 2>&1; then
  echo "[quick_pr] Creating PR via gh"
  body_file="PR_BODY.md"
  if [[ ! -f "$body_file" ]]; then
    echo "[quick_pr] $body_file not found; generating a minimal body."
    cat > "$body_file" <<'EOF'
This PR applies the Linux/WSL-only + Ruff-only + act-friendly CI automation pack.

Highlights:
- Keep only .github/workflows/ci.yml and codeql.yml.
- Ruff-only linting and formatting (no Black/isort/flake8).
- Pre-commit updated to ruff hooks only.
- Makefile updated with `pr` target and Ruff-only tasks.
- Hooks adjusted for Ruff-only.
- Scripts wired for local CI via `act`.

No functional code changes.
EOF
  fi
  if ! gh pr create -B "$BASE_BRANCH" -H "$BRANCH_NAME" -t "$PR_TITLE" -F "$body_file" "${LABEL_ARGS[@]}"; then
    echo "[quick_pr] gh failed to create PR — attempting to update labels on existing PR."
    if [[ ${#LABEL_ARGS[@]} -gt 0 ]]; then
      # Try to detect PR number and add labels
      PR_NUM=$(gh pr view --json number -q .number 2>/dev/null || echo "")
      if [[ -n "$PR_NUM" ]]; then
        echo "[quick_pr] Adding labels to PR #$PR_NUM: $LABELS"
        for ((i=0; i<${#LABEL_ARGS[@]}; i+=2)); do
          gh pr edit "$PR_NUM" --add-label "${LABEL_ARGS[i+1]}" || true
        done
      fi
    fi
  fi
else
  echo "[quick_pr] gh not installed; please open a PR manually."
fi

echo "[quick_pr] Done."
