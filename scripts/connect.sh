#!/bin/sh
# POSIX sh - Connect script for pass + HTTPS GitHub token
# Usage:
#   ./connect.sh -u <github-username> -t <token>
# or
#   GITHUB_TOKEN=... ./connect.sh -u <github-username>
# or (safer) ./connect.sh -u <github-username>  (will prompt for token)

set -eu

# --- Config: change KEYID if needed ---
KEYID="${KEYID:-8523D9D818B9C3C0}"
GNUPGHOME="${GNUPGHOME:-/root/.gnupg}"
PASSWORD_STORE_DIR="${PASSWORD_STORE_DIR:-/root/.password-store}"
REPO="${REPO:-HCE_v33_final_allinone_ready}"
GIT_REMOTE="${GIT_REMOTE:-origin}"

# --- Simple helpers ---
say() { printf '%s\n' "$*" >&2; }
err() { printf 'Error: %s\n' "$*" >&2; exit 1; }
have_cmd() { command -v "$1" >/dev/null 2>&1; }

# --- Parse args ---
USER_ARG=""
TOKEN_ARG=""

# POSIX getopts
while getopts "u:t:h" opt; do
  case "$opt" in
    u) USER_ARG="$OPTARG" ;;
    t) TOKEN_ARG="$OPTARG" ;;
    h) printf 'Usage: %s -u <github-username> [-t <token>]\n' "$0"; exit 0 ;;
    ?) printf 'Usage: %s -u <github-username> [-t <token>]\n' "$0"; exit 1 ;;
  esac
done
shift $((OPTIND -1))

if [ -z "$USER_ARG" ]; then
  err "GitHub username required. Usage: $0 -u <github-username> [-t <token>]"
fi

GITHUB_USER="$USER_ARG"

# If token provided via env, prefer that
if [ -n "${GITHUB_TOKEN:-}" ]; then
  TOKEN="$GITHUB_TOKEN"
elif [ -n "${TOKEN_ARG:-}" ]; then
  TOKEN="$TOKEN_ARG"
else
  # Prompt for token securely (no echo)
  printf 'Enter GitHub token (input hidden): ' >&2
  # Save stty state and disable echo if possible
  stty_orig=""
  if have_cmd stty; then
    stty_orig=$(stty -g 2>/dev/null || true) || true
    stty -echo 2>/dev/null || true
  fi
  # read one line
  IFS= read -r TOKEN || TOKEN=""
  # restore echo
  if [ -n "$stty_orig" ]; then
    stty "$stty_orig" 2>/dev/null || true
  else
    printf '\n' >&2
  fi
  printf '\n' >&2
fi

if [ -z "${TOKEN:-}" ]; then
  err "No token provided. Export GITHUB_TOKEN or pass -t, or enter it when prompted."
fi

export GNUPGHOME PASSWORD_STORE_DIR

# --- Prepare password-store ---
mkdir -p "$PASSWORD_STORE_DIR"
chmod 700 "$PASSWORD_STORE_DIR" 2>/dev/null || true

# Write KEYID into top-level .gpg-id (overwrite safely)
printf '%s\n' "$KEYID" > "$PASSWORD_STORE_DIR/.gpg-id"

# Normalize any existing .gpg-id files under tree (POSIX-safe loop)
if have_cmd find; then
  find "$PASSWORD_STORE_DIR" -type f -name .gpg-id 2>/dev/null | while IFS= read -r f; do
    printf '%s\n' "$KEYID" > "$f" || true
  done
fi

# Init pass (older versions may prompt; feed yes)
if ! have_cmd pass; then
  err "pass is not installed. Install pass and retry."
fi

# Use yes to answer prompts on very old pass versions
yes | pass init "$KEYID" >/dev/null 2>&1 || true

# Try reencrypt if supported
if pass help 2>/dev/null | grep -q reencrypt; then
  pass reencrypt >/dev/null 2>&1 || true
fi

# Remove any stale entries (no -f support on old versions)
yes | pass rm "git/https/github.com/$GITHUB_USER" >/dev/null 2>&1 || true
rm -f "$PASSWORD_STORE_DIR/git/https/github.com/$GITHUB_USER.gpg" 2>/dev/null || true

# Insert token into pass. Use -m if supported, else fallback to stdin interactive style.
say "Storing token into pass for git/https/github.com/$GITHUB_USER (encrypted)."
if pass insert -h 2>&1 | grep -q ' -m'; then
  pass insert -m "git/https/github.com/$GITHUB_USER" <<EOF
username=$GITHUB_USER
password=$TOKEN
EOF
else
  # Fallback: pipe the content into pass insert (older pass may still prompt for confirmation)
  { printf 'username=%s\n' "$GITHUB_USER"; printf 'password=%s\n' "$TOKEN"; } | pass insert "git/https/github.com/$GITHUB_USER" >/dev/null 2>&1 || true
fi

# --- Configure git to use the pass helper and HTTPS remote ---
git config --global credential.helper pass
# set origin to https if not already
if git remote -v | grep -q 'git@github.com:'; then
  git remote set-url "$GIT_REMOTE" "https://github.com/${GITHUB_USER}/${REPO}.git"
else
  # if remote already https but with different user/repo, still set to desired repo
  git remote set-url "$GIT_REMOTE" "https://github.com/${GITHUB_USER}/${REPO}.git"
fi

say "Attempting a git ls-remote (will use credential helper)..."
# Run a quick ls-remote to trigger credential helper; avoid exposing token
GIT_TERMINAL_PROMPT=0 git ls-remote "https://github.com/${GITHUB_USER}/${REPO}.git" || true

say "Done. Now try: git push (it should use pass as credential helper)."

# Security note
say "NOTE: Passing token on command-line can be visible to other local users via 'ps'."
say "Prefer: export GITHUB_TOKEN=...; ./connect.sh -u $GITHUB_USER  (or enter token interactively)."
exit 0
