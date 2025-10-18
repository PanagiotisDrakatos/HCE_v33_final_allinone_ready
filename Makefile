VENVDIR ?= .venv
PY      := $(VENVDIR)/bin/python
PIP     := $(VENVDIR)/bin/pip

.PHONY: venv install dev check lint fmt test pr
venv:
	@test -d $(VENVDIR) || python3 -m venv $(VENVDIR)

install: venv
	$(PIP) install -r requirements.txt

dev: venv
	$(PIP) install -U pip wheel
	# Ruff-only toolchain
	$(PIP) install ruff pytest pytest-xdist

check: lint test
	# Ruff-only checks (lint + format-check)
	$(VENVDIR)/bin/ruff check --output-format=github .
	$(VENVDIR)/bin/ruff format --check .

lint: venv
	$(VENVDIR)/bin/ruff check .

fmt:
	$(VENVDIR)/bin/ruff format .

test:
	$(VENVDIR)/bin/pytest -q

pr: dev
	@echo "==> Opening PR via scripts/quick_pr.sh"
	bash scripts/quick_pr.sh
