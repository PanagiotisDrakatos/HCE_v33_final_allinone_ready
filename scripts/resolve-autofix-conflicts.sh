#!/usr/bin/env bash
# Resolve ruff autofix merge conflicts during cherry-pick.
# Default: keep --theirs for *.py and config files, then continue.
# Usage:
#   scripts/resolve-autofix-conflicts.sh
# Options:
#   --dry-run   : show what would happen, don't change anything
#   --verbose   : print extra info
#   --keep-ours : keep ours for src/**/*.py (business code) & theirs for tests/configs

set -euo pipefail

DRY_RUN=0
VERBOSE=0
KEEP_OURS=0

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --verbose) VERBOSE=1 ;;
    --keep-ours) KEEP_OURS=1 ;;
    -h|--help)
      sed -n '1,25p' "$0"; exit 0 ;;
  esac
done

log() { echo -e "$@" >&2; }
vlog() { [[ $VERBOSE -eq 1 ]] && echo -e "$@" >&2 || true; }

# 1) safety checks
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || { log "❌ Not inside a git repo."; exit 2; }
if [[ ! -d .git ]]; then log "❌ Run from the repo root."; exit 2; fi

# Are we in a cherry-pick with conflicts?
if [[ ! -d ".git/CHERRY_PICK_HEAD" && ! -f ".git/CHERRY_PICK_HEAD" && ! -d ".git/sequencer" ]]; then
  log "ℹ️ Not in an active cherry-pick. Nothing to do."
  exit 0
fi

# 2) get conflicted files
mapfile -t CONFLICTS < <(git diff --name-only --diff-filter=U)
if [[ ${#CONFLICTS[@]} -eq 0 ]]; then
  log "ℹ️ No conflicted files detected."
  exit 0
fi

log "🧩 Conflicted files:"
printf ' - %s\n' "${CONFLICTS[@]}"

# 3) classify
PY_FILES=()
CFG_FILES=()
BUSINESS_FILES=()
TEST_FILES=()

for f in "${CONFLICTS[@]}"; do
  if [[ "$f" =~ \.py$ ]]; then
    if [[ "$f" =~ ^tests/ ]]; then TEST_FILES+=("$f"); else PY_FILES+=("$f"); fi
  elif [[ "$f" =~ (pyproject\.toml|ruff\.toml|\.pre-commit-config\.yaml|\.flake8|setup\.cfg|tox\.ini)$ ]]; then
    CFG_FILES+=("$f")
  else
    BUSINESS_FILES+=("$f")
  fi
done

apply_choice() {
  local mode="$1"; shift
  local files=("$@")
  [[ ${#files[@]} -eq 0 ]] && return 0
  if [[ $DRY_RUN -eq 1 ]]; then
    printf "DRY-RUN: would checkout %s for:\n" "$mode"
    printf '  - %s\n' "${files[@]}"
  else
    for f in "${files[@]}"; do
      vlog "→ git checkout ${mode} $f"
      git checkout "$mode" -- "$f"
    done
    git add "${files[@]}"
  fi
}

log "🔧 Applying resolution strategy…"
if [[ $KEEP_OURS -eq 1 ]]; then
  # ours for business code, theirs for tests/configs
  apply_choice --ours "${PY_FILES[@]}" "${BUSINESS_FILES[@]}"
  apply_choice --theirs "${TEST_FILES[@]}" "${CFG_FILES[@]}"
else
  # default: theirs for all .py & config (autofix commit wins)
  apply_choice --theirs "${PY_FILES[@]}" "${TEST_FILES[@]}" "${CFG_FILES[@]}"
  # leave non-Python business files to ours by default (safer)
  apply_choice --ours "${BUSINESS_FILES[@]}"
fi

# 4) continue cherry-pick
if [[ $DRY_RUN -eq 1 ]]; then
  log "DRY-RUN: would run 'git cherry-pick --continue'"
  exit 0
fi

if git diff --name-only --diff-filter=U | grep -q .; then
  log "⚠️ Some conflicts remain. Resolve manually then run:\n   git add <paths>\n   git cherry-pick --continue"
  exit 1
fi

log "✅ Conflicts resolved. Continuing cherry-pick…"
git cherry-pick --continue || {
  log "❌ cherry-pick failed to continue. Fix remaining issues and retry."; exit 1;
}

# Optional: quick formatting pass (ruff only)
if command -v ruff >/dev/null 2>&1; then ruff check . --fix || true; fi

log "🎉 Done."
