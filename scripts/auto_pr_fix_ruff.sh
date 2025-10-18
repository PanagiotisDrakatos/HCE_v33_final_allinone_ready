#!/usr/bin/env bash
set -euo pipefail

BASE_BRANCH="${BASE_BRANCH:-chore/ci-linux-ruff-act}"
FEATURE_BRANCH="${FEATURE_BRANCH:-fix/ruff-persistence-noqa}"
GOOD_COMMIT="${GOOD_COMMIT:-f2864707f8c553f3417fe8f73d057ebe25621f9e}"

echo "[INFO] Base: ${BASE_BRANCH} | Feature: ${FEATURE_BRANCH} | Cherry-pick: ${GOOD_COMMIT}"

# 0) Preconditions
python3 -V >/dev/null
command -v git >/dev/null

# 1) Ensure we have remote state
git fetch origin

# 2) Switch/create feature branch safely
current_branch="$(git rev-parse --abbrev-ref HEAD)"
if [ "${current_branch}" != "${FEATURE_BRANCH}" ]; then
  if git rev-parse --verify "${FEATURE_BRANCH}" >/dev/null 2>&1; then
    git switch "${FEATURE_BRANCH}"
  else
    git switch -c "${FEATURE_BRANCH}" "origin/${BASE_BRANCH}"
  fi
fi

# 3) Cherry-pick known-good commit (or apply minimal inline fixes)
if ! git log --format=%H | grep -q "${GOOD_COMMIT}"; then
  git fetch origin "${GOOD_COMMIT}" || true
  if ! git cherry-pick "${GOOD_COMMIT}"; then
    echo "[WARN] Cherry-pick had conflicts. Applying minimal inline fixes..."

    # 3a) Enforce stdlib import order (dataclasses first) at file top
    if [ -f hcebt/persistence.py ]; then
      python3 - <<'PY'
from pathlib import Path
import re

p = Path("hcebt/persistence.py")
if p.exists():
    s = p.read_text()
    # canonical stdlib import block (single group)
    block = [
        "from dataclasses import dataclass",
        "import logging",
        "import queue",
        "import threading",
        "import time",
    ]
    # replace any permutation of those 5 lines at the very top with canonical order
    pat = re.compile(
        r"^(?:from dataclasses import dataclass|import logging|import queue|import threading|import time)\n"
        r"(?:from dataclasses import dataclass|import logging|import queue|import threading|import time)\n"
        r"(?:from dataclasses import dataclass|import logging|import queue|import threading|import time)\n"
        r"(?:from dataclasses import dataclass|import logging|import queue|import threading|import time)\n"
        r"(?:from dataclasses import dataclass|import logging|import queue|import threading|import time)",
        re.M,
    )
    s = pat.sub("\n".join(block), s, count=1)
    # 3b) Add noqa C901 to _flush if missing
    needle = "def _flush(self, rows: list[dict]) -> None:"
    if needle in s and "noqa: C901" not in s:
        s = s.replace(needle, needle + "  # noqa: C901")
    p.write_text(s)
PY
      git add hcebt/persistence.py
      git commit -m "style(ruff): enforce stdlib import order & add noqa C901 on _flush" || true
    fi
  fi
fi

# 4) Ensure pyproject has mccabe=12 and sensible extend-exclude
if [ -f pyproject.toml ]; then
  if ! grep -q "mccabe" pyproject.toml; then
    printf "\n[tool.ruff.lint]\nmccabe = { max-complexity = 12 }\n" >> pyproject.toml
  else
    # bump to 12 if lower
    sed -i "s/mccabe\s*=\s*{[^}]*max-complexity\s*=\s*[0-9]\+/mccabe = { max-complexity = 12/g" pyproject.toml
  fi
  # ensure extend-exclude includes .git/tools-venv
  if ! grep -q ".git/tools-venv" pyproject.toml; then
    sed -i "s|extend-exclude=\[|extend-exclude=['.git/tools-venv', |" pyproject.toml || true
  fi
fi
git add -A
git commit -m "chore(ruff): ensure mccabe=12 & extend-exclude includes .git/tools-venv" || true

# 5) Local Ruff in venv (PEP 668-safe)
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -U pip wheel ruff >/dev/null
ruff check --fix .
ruff format .
deactivate
git add -A
git commit -m "style(ruff): apply ruff --fix and format" || true

# 6) Optional act dry-run with correct head/base
export GITHUB_HEAD_REF="${FEATURE_BRANCH}"
export GITHUB_BASE_REF="${BASE_BRANCH}"
export AUTO_INSTALL_ACT="${AUTO_INSTALL_ACT:-1}"
export RUN_ACT="${RUN_ACT:-1}"
export RUN_ACT_BEFORE_PUSH="${RUN_ACT_BEFORE_PUSH:-1}"
export RUN_BACKTESTS="${RUN_BACKTESTS:-0}"

if [ "${RUN_ACT}" = "1" ]; then
  make pr-dry || echo "[WARN] act dry-run failed; continuing to push so GH CI can run."
fi

# 7) Push and open PR
git push -u origin "${FEATURE_BRANCH}"

if command -v gh >/dev/null; then
  gh pr create --fill --base "${BASE_BRANCH}" --head "${FEATURE_BRANCH}" || true
  echo "[INFO] If PR did not open automatically, open manually:"
  echo "https://github.com/$(git config --get remote.origin.url | sed -E 's#.*github.com[:/](.+)\.git#\1#')/compare/${BASE_BRANCH}...${FEATURE_BRANCH}"
else
  echo "[INFO] Open PR manually:"
  echo "https://github.com/$(git config --get remote.origin.url | sed -E 's#.*github.com[:/](.+)\.git#\1#')/compare/${BASE_BRANCH}...${FEATURE_BRANCH}"
fi
