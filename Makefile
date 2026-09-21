# ──────────────────────────────────────────────────────────────────────────────
# Linux/WSL-only Makefile (Ruff-only toolchain)
# Tip: override with env, π.χ. RUFF_FIX=0 make pr
# ──────────────────────────────────────────────────────────────────────────────

SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.ONESHELL:
.DEFAULT_GOAL := help

# Paths
VENV ?= .venv
BIN  := $(VENV)/bin
PY   := $(BIN)/python
PIP  := $(BIN)/pip
RUFF := $(BIN)/ruff
PYTEST := $(BIN)/pytest
# κάνε διαθέσιμο το .venv/bin σε ΟΛΑ τα targets (ώστε να βρίσκονται ruff/pytest)
export PATH := $(abspath $(BIN)):$(PATH)

# Behavior toggles
RUFF_FIX ?= 1               # 1: autofix, 0: check only
RUN_BACKTESTS ?= 1          # 1: run tests, 0: skip (fast)
AUTO_INSTALL_ACT ?= 1       # 1: auto-install nektos/act if missing
# Act runner images with Node+sudo preinstalled
ACT_PLATFORM ?= ubuntu-latest=ghcr.io/catthehacker/ubuntu:full-latest,ubuntu-24.04=ghcr.io/catthehacker/ubuntu:full-latest





# Overlay fast-apply (optional URLs; αν λείπουν, περιμένει local αρχεία)
PACK ?= HCE_v33_linux_ruff_auto_pack.tar.gz
APPLY ?= apply_ci_pack.sh
PACK_URL ?=
APPLY_URL ?=

# ─────────────────────────────── Helpers ─────────────────────────────────────
.PHONY: _ensure_venv _ensure_ruff _msg

_msg:
	@printf "\n\033[1;36m▶ %s\033[0m\n" "$(MSG)"

_ensure_venv:
	@if [ ! -x "$(PY)" ]; then \
		# If a Windows-style venv exists, remove it and recreate POSIX venv; \
		# otherwise just create a fresh venv. \
		if [ -x "$(VENV)/Scripts/python.exe" ] || [ -x "$(VENV)/Scripts/python" ]; then \
			echo "⚠️  Detected Windows-style venv at $(VENV)/Scripts — recreating POSIX venv"; \
			rm -rf "$(VENV)"; \
		fi; \
		$(MAKE) venv; \
	fi

_ensure_ruff: _ensure_venv
	@if ! "$(RUFF)" --version >/dev/null 2>&1; then \
		# Use python -m pip to be resilient if pip script is missing \
		"$(PY)" -m pip install -U pip wheel; \
		"$(PY)" -m pip install ruff; \
	fi

# ─────────────────────────────── Targets ─────────────────────────────────────

.PHONY: help
help:
	@echo "Make targets (Linux/WSL + Ruff-only):"
	@echo "  venv              Create .venv and install deps (requirements*, editable project)"
	@echo "  deps              Reinstall dev deps (ruff/pytest)"
	@echo "  fmt               Ruff format + autofix lint"
	@echo "  fmt-check         Format check + lint check (no changes)"
	@echo "  lint              Ruff lint (GitHub output)"
	@echo "  lint-fix          Create venv and run Ruff auto-fix + format"
	@echo "  test              pytest (fast gate)"
	@echo "  pr                End-to-end pre-PR run + quick_pr.sh"
	@echo "  pr-dry            Dry-run quick_pr (act πριν push, χωρίς push/PR)"
	@echo "  ci-local          Run act jobs (lint/tests/pr-guard) locally"
	@echo "  ci-local-fast     Same με reuse/bind/pull=false για ταχύτητα"
	@echo "  ci-apply          Fast apply του automation overlay (pack + script)"
	@echo "  hooks             Install pre-commit & pre-push hook"
	@echo "  clean             Remove .venv, caches, artifacts"
	@echo "  verify            fast + runtime proof + evidence receipt"
	@echo "  verify-check      Fail if the receipt is stale or not PASS"
	@echo "  clean-runtime     Tear down verify compose projects (project-scoped)"
	@echo "  project-reset     Safer: wipe only repo caches/.venv and pre-pull act image"

.PHONY: venv
venv:
	@printf "\n\033[1;36m▶ Create venv & install deps\033[0m\n"
	@if ! python3 -m venv $(VENV) 2>/dev/null; then \
		echo "⚠️  venv creation failed. Trying with ensurepip..."; \
		python3 -m venv $(VENV) --without-pip || exit 1; \
		$(VENV)/bin/python -m ensurepip --default-pip || exit 1; \
	fi
	@$(VENV)/bin/python -m pip install --quiet -U pip wheel 2>/dev/null || $(VENV)/bin/python -m pip install -U pip wheel
	@[ -f requirements.txt ]      && $(VENV)/bin/pip install -r requirements.txt || true
	@[ -f requirements-dev.txt ]  && $(VENV)/bin/pip install -r requirements-dev.txt || true
	@[ -f pyproject.toml ]        && $(VENV)/bin/pip install -e . || true
	@echo "✅ Virtualenv ready in $(VENV)"

.PHONY: deps
deps: _ensure_venv
	@$(MAKE) _msg MSG="Install dev tools (ruff/pytest)"
	$(VENV)/bin/pip install -U ruff pytest

.PHONY: fmt
fmt: _ensure_ruff
	@$(MAKE) _msg MSG="Ruff: format + autofix"
	$(RUFF) format .
	$(RUFF) check --fix --force-exclude .

.PHONY: fmt-check
fmt-check: _ensure_ruff
	@$(MAKE) _msg MSG="Ruff: format check + lint check"
	$(RUFF) format --check .
	$(RUFF) check --force-exclude .

.PHONY: lint
lint: _ensure_ruff
	@$(MAKE) _msg MSG="Ruff: lint (GitHub output)"
	$(RUFF) check --output-format=github --force-exclude .

# New: quick auto-fix convenience
.PHONY: lint-fix
lint-fix: _ensure_ruff
	@$(MAKE) _msg MSG="Creating venv and running Ruff auto-fix..."
	$(RUFF) check --fix --force-exclude .
	$(RUFF) format .

.PHONY: test
test: _ensure_venv
	@$(MAKE) _msg MSG="pytest (fast)"
	$(PYTEST) -q || (echo "❌ pytest failed" && exit 1)

# ─────────────────────────── PR flows (quick_pr.sh) ──────────────────────────

.PHONY: pr
pr: _ensure_ruff
ifeq ($(RUFF_FIX),1)
	$(MAKE) fmt
else
	$(MAKE) fmt-check
endif
	$(MAKE) lint
	@if [ "$(RUN_BACKTESTS)" != "0" ]; then $(MAKE) test; else echo "⏭️  skipping tests (RUN_BACKTESTS=0)"; fi
	AUTO_INSTALL_ACT=$(AUTO_INSTALL_ACT) RUN_BACKTESTS=$(RUN_BACKTESTS) ACT_PLATFORM="$(ACT_PLATFORM)" bash ./scripts/quick_pr.sh

.PHONY: pr-dry
pr-dry:
	@# Ensure repo-local tooling venv to avoid PEP 668
	@bash .scripts/bootstrap_tools.sh
	@$(MAKE) _msg MSG="quick_pr DRY-RUN (act before push, no push/PR)"
	DRY_RUN=1 RUN_ACT=1 RUN_ACT_BEFORE_PUSH=1 RUN_ACT_AFTER_PUSH=0 RUN_BACKTESTS=$(RUN_BACKTESTS) AUTO_INSTALL_ACT=$(AUTO_INSTALL_ACT) ACT_PLATFORM="$(ACT_PLATFORM)" bash ./scripts/quick_pr.sh

# ───────────────────────────── Local CI (act) ────────────────────────────────

.PHONY: ci-local
ci-local:
	@$(MAKE) _msg MSG="act (lint/tests/pr-guard) — simulate pull_request"
	DRY_RUN=1 RUN_ACT=1 RUN_ACT_BEFORE_PUSH=1 RUN_ACT_AFTER_PUSH=0 RUN_BACKTESTS=$(RUN_BACKTESTS) AUTO_INSTALL_ACT=$(AUTO_INSTALL_ACT) ACT_PLATFORM="$(ACT_PLATFORM)" bash ./scripts/quick_pr.sh

.PHONY: ci-local-fast
ci-local-fast:
	@$(MAKE) _msg MSG="act fast (reuse/bind, no pull)"
	DRY_RUN=1 RUN_ACT=1 RUN_ACT_BEFORE_PUSH=1 RUN_ACT_AFTER_PUSH=0 RUN_BACKTESTS=$(RUN_BACKTESTS) AUTO_INSTALL_ACT=$(AUTO_INSTALL_ACT) ACT_REUSE=1 ACT_BIND=1 ACT_PULL=0 ACT_PLATFORM="$(ACT_PLATFORM)" bash ./scripts/quick_pr.sh

# ───────────────────────────── Overlay fast-apply ────────────────────────────

.PHONY: ci-apply
ci-apply:
	@$(MAKE) _msg MSG="Automation pack: apply overlay"
	@if [ ! -f "$(PACK)" ]; then \
		if [ -n "$(PACK_URL)" ]; then \
			echo "↓ Download pack from $(PACK_URL)"; \
			curl -fsSL -o "$(PACK)" "$(PACK_URL)"; \
		else \
			echo "❌ $(PACK) not found and PACK_URL empty"; exit 1; \
		fi; \
	fi
	@if [ ! -f "$(APPLY)" ]; then \
		if [ -n "$(APPLY_URL)" ]; then \
			echo "↓ Download apply script from $(APPLY_URL)"; \
			curl -fsSL -o "$(APPLY)" "$(APPLY_URL)"; \
		else \
			echo "❌ $(APPLY) not found and APPLY_URL empty"; exit 1; \
		fi; \
	fi
	chmod +x "$(APPLY)"
	bash "$(APPLY)" "$(PACK)"

# ───────────────────────────── Dev UX helpers ────────────────────────────────

.PHONY: hooks
hooks: _ensure_venv
	@$(MAKE) _msg MSG="Install pre-commit & enable pre-push hook"
	@if command -v pre-commit >/dev/null 2>&1; then \
		pre-commit install -f || true; \
		pre-commit install --hook-type pre-push -f || true; \
	else \
		echo "ℹ️ pre-commit not found (optional)"; \
	fi
	@chmod +x hooks/pre-push || true
	@echo "✅ Hooks configured"

.PHONY: clean
clean:
	@$(MAKE) _msg MSG="Clean venv & caches"
	rm -rf "$(VENV)" .ruff_cache .pytest_cache .mypy_cache build dist coverage.xml .coverage
	@echo "🧹 done"

# ───────────────────────────── Verify plane ──────────────────────────────────
# `deep-reset` was removed: it stopped and removed every container on the host
# and pruned all images and volumes host-wide, which is unsafe on any shared
# node. Use `clean-runtime` (project-scoped) or `project-reset` (repo caches).
.PHONY: verify verify-check clean-runtime
verify:
	@$(MAKE) _msg MSG="verify: fast + runtime proof + receipt"
	$(PY) scripts/verify.py fast
	$(PY) scripts/verify.py runtime
	$(PY) scripts/verify.py receipt

verify-check:
	$(PY) scripts/verify.py check --receipt .verify/receipt.json

clean-runtime:
	@$(MAKE) _msg MSG="Tear down verify compose projects (project-scoped)"
	$(PY) scripts/verify.py clean

# Safer alternative: only project-related cleanup (keeps other Docker stuff)
.PHONY: project-reset
project-reset:
	@$(MAKE) _msg MSG="🧼 Project-only reset (keeps other Docker images/volumes)"
	rm -rf "$(VENV)" .ruff_cache .pytest_cache .mypy_cache .act-cache build dist coverage.xml .coverage *.egg-info
	$(MAKE) venv
	@img="$$(echo '$(ACT_PLATFORM)' | awk -F= '{print $$2}')" ; \
	if [ -n "$$img" ]; then echo "🐳 docker pull $$img" ; docker pull "$$img" || true ; fi
	@echo "✅ Project reset complete."

# ─────────────────────────────────────────────────────────────────────────────
# End of file
