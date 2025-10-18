#!/usr/bin/env bash
# 1) Νέο branch
git checkout -b chore/ci-ruff-only-cleanup

# 2) Διέγραψε όλα τα παλιά workflows εκτός από ci.yml & codeql.yml
find .github/workflows -type f -name '*.yml' ! -name 'ci.yml' ! -name 'codeql.yml' -print -exec git rm -f {} \;

# 3) Γράψε καθαρό Ruff-only CI (ubuntu-only, pip & ruff cache, PR Guard)
cat > .github/workflows/ci.yml <<'YAML'
name: CI (Linux + Ruff)

on:
  push:
    branches: [ main, dev, develop ]
  pull_request:
    branches: [ main, dev, develop ]

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read

env:
  PIP_DISABLE_PIP_VERSION_CHECK: 1
  PYTHONUNBUFFERED: 1

jobs:
  lint:
    name: Ruff Lint & Format (check)
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
      - name: Cache Ruff
        uses: actions/cache@v4
        with:
          path: .ruff_cache
          key: ${{ runner.os }}-ruff-${{ hashFiles('pyproject.toml') }}
          restore-keys: |
            ${{ runner.os }}-ruff-
      - name: Install ruff
        run: |
          python -m pip install -U pip
          pip install ruff
      - name: Ruff check
        run: ruff check --output-format=github --force-exclude .
      - name: Ruff format (check only)
        run: ruff format --check .

  tests:
    name: Unit Tests
    runs-on: ubuntu-latest
    needs: [lint]
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
      - name: Install deps
        run: |
          python -m pip install -U pip wheel
          if [ -f requirements.txt ]; then pip install -r requirements.txt; fi
          if [ -f requirements-dev.txt ]; then pip install -r requirements-dev.txt; fi
          if [ -f pyproject.toml ]; then pip install -e .; fi
          pip install pytest
      - name: Run pytest
        run: pytest -q

  pr-guard:
    name: PR Guard (merge/conflicts/policy)
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Ensure PR merges cleanly into base
        shell: bash
        run: |
          set -euo pipefail
          echo "Base: $GITHUB_BASE_REF  Head: $GITHUB_HEAD_REF"
          git fetch origin "$GITHUB_BASE_REF" "$GITHUB_HEAD_REF"
          git checkout -b pr-merge-test "origin/$GITHUB_BASE_REF"
          if ! git merge --no-commit --no-ff "origin/$GITHUB_HEAD_REF"; then
            echo "::error::This PR cannot be merged cleanly into ${GITHUB_BASE_REF}. Please rebase."
            exit 1
          fi
          echo "✅ Clean merge test passed."
      - name: Check branch is not behind base
        shell: bash
        run: |
          set -euo pipefail
          git fetch origin "$GITHUB_BASE_REF"
          BEHIND=$(git rev-list --count HEAD.."origin/$GITHUB_BASE_REF")
          if [ "$BEHIND" -gt 0 ]; then
            echo "::error::Branch is $BEHIND commits behind ${GITHUB_BASE_REF}. Please rebase/merge."
            exit 1
          fi
          echo "✅ Branch is up to date with base."
      - name: Disallow merge commits in PR history
        shell: bash
        run: |
          set -euo pipefail
          git fetch origin "$GITHUB_BASE_REF"
          MERGES=$(git rev-list --merges --count "origin/$GITHUB_BASE_REF"..HEAD)
          if [ "$MERGES" -gt 0 ]; then
            echo "::error::PR contains merge commits. Please rebase on ${GITHUB_BASE_REF}."
            exit 1
          fi
          echo "✅ No merge commits in PR history."
      - name: Forbid Windows-only files & non-Ruff linters
        shell: bash
        run: |
          set -euo pipefail
          # Allow .cmd files in scripts/ directory for local usage, forbid elsewhere
          if git ls-files -z | grep -E -z '\.(bat|ps1)$' || (git ls-files -z | grep -E -z '\.cmd$' | grep -vz '^scripts/'); then
            echo "::error::Windows-only scripts (*.cmd|*.bat|*.ps1) are not allowed outside scripts/ directory."; exit 1
          fi
          if git grep -nE '\b(black|flake8|pylint|isort)\b' -- . ':!*.md' ':!CHANGELOG*' ':!.github/workflows/codeql.yml' ; then
            echo "::error::Found disallowed linters/configs (black/flake8/pylint/isort). Use Ruff only."; exit 1
          fi
          echo "✅ Policy checks passed."
      - name: Enforce basic Conventional PR title
        shell: bash
        run: |
          set -euo pipefail
          title="${{ github.event.pull_request.title }}"
          if [[ ! "$title" =~ ^(feat|fix|chore|refactor|docs|test|perf)(\(.+\))?:\ .{1,}$ ]]; then
            echo "::error::PR title must follow Conventional Commits (e.g., 'feat: ...', 'fix(parser): ...')."
            exit 1
          fi
          echo "✅ PR title OK."
YAML

# 4) Επιβεβαίωσε ότι δεν έμειναν black/isort/pylint
git grep -nE '\b(black|flake8|pylint|isort)\b' -- . || true

# 5) Commit & push
git add -A
git commit -m "ci: Ruff-only; remove black/isort; linux-only runners; add PR guard"
git push -u origin chore/ci-ruff-only-cleanup
