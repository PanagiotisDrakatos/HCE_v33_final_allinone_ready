#!/usr/bin/env bash
set -euo pipefail

# ============================================
#  Cleanup virtualenvs & Ruff caches (WSL/Linux/macOS)
#  - Project-only or Home-wide cleanup
#  - Dry-run mode & confirmation prompts
#  - Generates a deletion report under run_artifacts/
# ============================================

# Defaults
SCOPE="project"        # project | home
DRYRUN="false"
YES="false"
PURGE_PIP_CACHE="false"
PURGE_GLOBAL_RUFF="false"

usage() {
  cat <<'USAGE'
Usage:
  cleanup_envs.sh [options]
Options:
  --scope [project|home]   Cleanup scope (default: project)
                           project: only in current repo
                           home:    search & clean across $HOME
  --dry-run                Show what would be deleted, do not delete
  --yes                    Do not prompt for confirmation (non-interactive)
  --purge-pip-cache        Also delete ~/.cache/pip
  --purge-global-ruff      Try to uninstall global Ruff (pip/pipx) and clear its caches
  -h, --help               Show this help

Examples:
  bash scripts/cleanup_envs.sh --scope project
  bash scripts/cleanup_envs.sh --scope home --dry-run
  bash scripts/cleanup_envs.sh --scope home --yes --purge-pip-cache --purge-global-ruff
USAGE
}

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --scope) SCOPE="${2:-}"; shift 2;;
    --dry-run) DRYRUN="true"; shift;;
    --yes) YES="true"; shift;;
    --purge-pip-cache) PURGE_PIP_CACHE="true"; shift;;
    --purge-global-ruff) PURGE_GLOBAL_RUFF="true"; shift;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown option: $1"; usage; exit 2;;
  esac
done

# Validate scope
if [[ "$SCOPE" != "project" && "$SCOPE" != "home" ]]; then
  echo "Invalid --scope: $SCOPE (allowed: project|home)"; exit 2;
fi

ROOT="$(pwd)"
ART_DIR="${ROOT}/run_artifacts"
mkdir -p "$ART_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
REPORT="${ART_DIR}/cleanup_report_${SCOPE}_${STAMP}.txt"

log() { echo -e "$*"; }
log_to_report() { echo -e "$*" >> "$REPORT"; }

# Build deletion candidates
declare -a PATHS=()

if [[ "$SCOPE" == "project" ]]; then
  # Only current repo tree
  mapfile -t P1 < <(find "$ROOT" -maxdepth 2 -type d -name ".venv*" 2>/dev/null || true)
  mapfile -t P2 < <(find "$ROOT" -type d -name ".ruff_cache" 2>/dev/null || true)
  mapfile -t P3 < <(find "$ROOT" -type d -name ".pytest_cache" 2>/dev/null || true)
  mapfile -t P4 < <(find "$ROOT" -type d -name "__pycache__" 2>/dev/null || true)
  PATHS+=("${P1[@]}" "${P2[@]}" "${P3[@]}" "${P4[@]}")
else
  # Home-wide search
  HOME_DIR="${HOME}"
  mapfile -t H1 < <(find "$HOME_DIR" -type d -name ".venv*" 2>/dev/null || true)
  mapfile -t H2 < <(find "$HOME_DIR" -type d -name ".ruff_cache" 2>/dev/null || true)
  mapfile -t H3 < <(find "$HOME_DIR" -type d -name ".pytest_cache" 2>/dev/null || true)
  mapfile -t H4 < <(find "$HOME_DIR" -type d -name "__pycache__" 2>/dev/null || true)
  PATHS+=("${H1[@]}" "${H2[@]}" "${H3[@]}" "${H4[@]}")
fi

# De-duplicate & filter existing
declare -A SEEN=()
CLEAN_LIST=()
for p in "${PATHS[@]}"; do
  [[ -z "${p:-}" ]] && continue
  [[ -d "$p" ]] || continue
  if [[ -z "${SEEN[$p]:-}" ]]; then
    SEEN[$p]=1
    CLEAN_LIST+=("$p")
  fi
done

# Summary
log "⚙️  Cleanup scope: $SCOPE"
log "🧪 Dry-run: $DRYRUN"
log "🧹 Purge pip cache: $PURGE_PIP_CACHE"
log "🧽 Purge global Ruff: $PURGE_GLOBAL_RUFF"
log "📝 Report: $REPORT"
log ""
log "🔎 Found ${#CLEAN_LIST[@]} paths to clean:"
for p in "${CLEAN_LIST[@]}"; do log "   • $p"; done
log ""

confirm() {
  if [[ "$YES" == "true" ]]; then return 0; fi
  read -r -p "Proceed with cleanup? [y/N] " ans
  [[ "${ans,,}" == "y" || "${ans,,}" == "yes" ]]
}

if ! confirm; then
  log "❎ Aborted by user."
  exit 0
fi

# Write header to report
log_to_report "Cleanup started: $(date)"
log_to_report "Scope: $SCOPE | Dry-run: $DRYRUN | Purge pip cache: $PURGE_PIP_CACHE | Purge global Ruff: $PURGE_GLOBAL_RUFF"
log_to_report "----------------------------------------"

delete_path() {
  local target="$1"
  if [[ "$DRYRUN" == "true" ]]; then
    log "DRY-RUN  rm -rf \"$target\""
    log_to_report "DRY-RUN  $target"
  else
    rm -rf "$target"
    log "✅ Deleted: $target"
    log_to_report "DELETED  $target"
  fi
}

# Deactivate any active venv (ignore errors)
deactivate 2>/dev/null || true

# Delete items
for p in "${CLEAN_LIST[@]}"; do
  delete_path "$p"
done

# Optional: purge pip cache
if [[ "$PURGE_PIP_CACHE" == "true" ]]; then
  for pc in "$HOME/.cache/pip"; do
    [[ -d "$pc" ]] && delete_path "$pc"
  done
fi

# Optional: purge global ruff
if [[ "$PURGE_GLOBAL_RUFF" == "true" ]]; then
  if [[ "$DRYRUN" == "true" ]]; then
    log "DRY-RUN  python3 -m pip uninstall -y ruff || true"
    log "DRY-RUN  pipx uninstall ruff || true"
    log "DRY-RUN  rm -rf ~/.cache/ruff ~/.local/share/ruff"
    log_to_report "DRY-RUN  uninstall ruff + clear ruff caches"
  else
    python3 -m pip uninstall -y ruff >/dev/null 2>&1 || true
    pipx uninstall ruff >/dev/null 2>&1 || true
    rm -rf "$HOME/.cache/ruff" "$HOME/.local/share/ruff"
    log "✅ Global Ruff uninstalled & caches cleared (if installed)."
    log_to_report "UNINSTALLED ruff (pip/pipx) & cleared caches"
  fi
fi

log_to_report "----------------------------------------"
log_to_report "Cleanup finished: $(date)"
log ""
log "🏁 Done. Report: $REPORT"
