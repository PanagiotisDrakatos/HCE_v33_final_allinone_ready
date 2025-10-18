#!/usr/bin/env bash
set -euo pipefail

BRANCH="${BRANCH:-chore/ci-ruff-only-$(date +%Y%m%d-%H%M%S)}"
TITLE="${TITLE:-chore(ci): Linux-only + Ruff-only CI pack}"
BODY="${BODY:-Automated PR via quick_pr.sh}"
LABELS="${LABELS:-ci}"
BASE="${BASE:-main}"

RUFF_FIX="${RUFF_FIX:-1}"
RUN_BACKTESTS="${RUN_BACKTESTS:-1}"

RUN_ACT="${RUN_ACT:-1}"
RUN_ACT_BEFORE_PUSH="${RUN_ACT_BEFORE_PUSH:-1}"
RUN_ACT_AFTER_PUSH="${RUN_ACT_AFTER_PUSH:-0}"
AUTO_INSTALL_ACT="${AUTO_INSTALL_ACT:-1}"
ACT_REUSE="${ACT_REUSE:-1}"
ACT_BIND="${ACT_BIND:-1}"
ACT_PULL="${ACT_PULL:-0}"

# ⬇️ ΣΙΓΟΥΡΟ default για πλήρη συμβατότητα με GitHub (ubuntu-24.04)
ACT_PLATFORM="${ACT_PLATFORM:-ubuntu-24.04=ghcr.io/catthehacker/ubuntu:act-24.04}"
# ⬇️ Προαιρετικά: πολλαπλά mappings (αν προτιμάς, άφησέ το ως έχει)
ACT_PLATFORMS="${ACT_PLATFORMS:-ubuntu-24.04=ghcr.io/catthehacker/ubuntu:act-24.04 ubuntu-latest=ghcr.io/catthehacker/ubuntu:act-24.04}"

ACT_CONTAINERLESS="${ACT_CONTAINERLESS:-0}"
DRY_RUN="${DRY_RUN:-0}"

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
[[ -z "${ROOT}" ]] && { echo "❌ Not a git repo"; exit 1; }
cd "$ROOT"

# Prefer local .bin early
export PATH="$PWD/.bin:$PATH"

log(){ printf "%s\n" "$*" >&2; }
die(){ log "❌ $*"; exit 1; }
has(){ command -v "$1" >/dev/null 2>&1; }

ACT_BIN="${ACT_BIN:-act}"
if [[ -x ".bin/act" ]]; then ACT_BIN="$PWD/.bin/act"; fi
if [[ -x ".bin/act.exe" ]]; then ACT_BIN="$PWD/.bin/act.exe"; fi

ensure_act() {
  if has "$ACT_BIN"; then return 0; fi
  if has act; then ACT_BIN="$(command -v act)"; return 0; fi
  [[ "$AUTO_INSTALL_ACT" != "1" ]] && die "'act' not found and AUTO_INSTALL_ACT=0"
  log "⚙️  Installing 'act'…"
  if has brew;  then brew install act && ACT_BIN="$(command -v act)" && return 0; fi
  if has scoop; then scoop install act && ACT_BIN="$(command -v act)" && return 0; fi
  if has choco; then choco install -y act-cli && ACT_BIN="$(command -v act)" && return 0; fi
  mkdir -p .bin
  arch="$(uname -m || echo x86_64)"; case "$arch" in x86_64|amd64) arch="x86_64";; aarch64|arm64) arch="arm64";; *) arch="x86_64";; esac
  sys="$(uname -s || echo)"
  case "$sys" in
    *MINGW*|*MSYS*|*CYGWIN*|Windows_NT)
      if has powershell; then
        url="https://github.com/nektos/act/releases/latest/download/act_Windows_${arch}.zip"
        tmp="$(mktemp -d)"
        curl -fsSL -o "$tmp/act.zip" "$url" || die "act download failed"
        powershell -NoProfile -Command "Expand-Archive -Path '$tmp/act.zip' -DestinationPath '$tmp' -Force" || die "Expand-Archive failed"
        mv "$tmp/act.exe" .bin/act.exe || die "move act.exe failed"
        chmod +x .bin/act.exe
        ACT_BIN="$PWD/.bin/act.exe"
      else
        die "PowerShell not found to unzip act.exe; install act via scoop/choco."
      fi
      ;;
    Darwin)
      url="https://github.com/nektos/act/releases/latest/download/act_Darwin_${arch}.tar.gz"
      tmp="$(mktemp -d)"
      curl -fsSL "$url" -o "$tmp/act.tgz" || die "act download failed"
      tar -xzf "$tmp/act.tgz" -C "$tmp" || die "untar failed"
      mv "$tmp/act" .bin/act && chmod +x .bin/act
      ACT_BIN="$PWD/.bin/act"
      ;;
    Linux|*)
      url="https://github.com/nektos/act/releases/latest/download/act_Linux_${arch}.tar.gz"
      tmp="$(mktemp -d)"
      curl -fsSL "$url" -o "$tmp/act.tgz" || die "act download failed"
      tar -xzf "$tmp/act.tgz" -C "$tmp" || die "untar failed"
      mv "$tmp/act" .bin/act && chmod +x .bin/act
      ACT_BIN="$PWD/.bin/act"
      ;;
  esac
  log "✅ act: $ACT_BIN"
}

supports_flag() { "$ACT_BIN" --help 2>&1 | grep -q -- "$1"; }

ensure_docker() {
  if ! has docker; then
    log "⚠️  Docker not found. 'act' requires Docker/Podman."
    return 1
  fi
  if ! docker info >/dev/null 2>&1; then
    log "⚠️  Docker engine is not running."
    return 1
  fi
  return 0
}

run_act() {
  ensure_act
  ensure_docker || die "Docker engine not available"

  local jobs=(-j lint -j tests -j pr-guard)
  [[ "$RUN_BACKTESTS" == "1" ]] && jobs+=(-j backtests)

  local reuse=(); [[ "$ACT_REUSE" == "1" ]] && reuse+=(--reuse)
  local bind=();  [[ "$ACT_BIND"  == "1" ]] && bind+=(--bind)
  local pull=();  [[ "$ACT_PULL"  == "1" ]] && pull+=(--pull)
  local containerless=()
  if [[ "$ACT_CONTAINERLESS" == "1" ]]; then
    if supports_flag "--containerless"; then containerless+=(--containerless); else log "ℹ️  '--containerless' not supported; skipping."; fi
  fi

  # Build platform mappings (single + multi) για πλήρη συμβατότητα με GitHub runner images
  local platform_args=()

  # βασικό mapping (single)
  if [[ -n "${ACT_PLATFORM:-}" ]]; then
    if [[ "$ACT_PLATFORM" == *"="* ]]; then
      platform_args+=(-P "$ACT_PLATFORM")
      ACT_IMAGE="${ACT_PLATFORM#*=}"
    else
      # Αν δοθεί μόνο image, χαρτογράφησέ το σε ubuntu-24.04/ubuntu-latest
      ACT_IMAGE="$ACT_PLATFORM"
      platform_args+=(-P "ubuntu-24.04=$ACT_IMAGE" -P "ubuntu-latest=$ACT_IMAGE")
    fi
  fi

  # επιπλέον mappings (multi), π.χ. "ubuntu-24.04=... ubuntu-latest=..."
  for map in $ACT_PLATFORMS; do
    [[ -n "$map" ]] && platform_args+=(-P "$map")
  done

  log "▶️  $ACT_BIN pull_request ${jobs[*]}"
  "$ACT_BIN" "${platform_args[@]}" "${reuse[@]}" "${bind[@]}" "${pull[@]}" "${containerless[@]}" pull_request "${jobs[@]}"
}

# ruff on PATH ώστε fmt/lint να τρέχουν πριν το PR
if [[ -x ".venv/bin/ruff" ]]; then export PATH="$PWD/.venv/bin:$PATH"; fi
# If ruff still missing, use tooling venv to avoid PEP 668
if ! has ruff; then
  VENV_DIR="${VENV_DIR:-.git/tools-venv}"
  if [[ -x "${VENV_DIR}/bin/ruff" ]]; then
    export PATH="${VENV_DIR}/bin:$PATH"
  elif [[ -x "${VENV_DIR}/bin/python" ]]; then
    "${VENV_DIR}/bin/python" -m pip install -q ruff 2>/dev/null || true
    export PATH="${VENV_DIR}/bin:$PATH"
  fi
fi

# Run act BEFORE push if requested
if [[ "$RUN_ACT" == "1" && "$RUN_ACT_BEFORE_PUSH" == "1" ]]; then
  run_act
fi

# DRY RUN exits right before git ops
if [[ "$DRY_RUN" == "1" ]]; then
  log "DRY_RUN=1: exiting before git operations."
  exit 0
fi

# Create/update branch, commit & push
cur="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$cur" != "$BRANCH" ]]; then git checkout -B "$BRANCH"; fi
if [[ -n "$(git status --porcelain)" ]]; then
  git add -A
  git commit -m "$TITLE" || true
fi
git push -u origin "$BRANCH"

# Create PR with gh if available
if has gh; then
  pr_args=(--title "$TITLE" --body "$BODY" --base "$BASE")
  IFS=',' read -ra L <<< "$LABELS"; for l in "${L[@]}"; do pr_args+=(--label "$(echo "$l" | xargs)"); done
  gh pr create "${pr_args[@]}" || log "⚠️  gh pr create failed; open PR manually."
else
  log "ℹ️  'gh' not found — open PR manually: origin/$BRANCH → $BASE"
fi

# Optionally run act AFTER push
if [[ "$RUN_ACT" == "1" && "$RUN_ACT_AFTER_PUSH" == "1" ]]; then
  run_act
fi

log "✅ quick_pr.sh complete."
