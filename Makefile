VENVDIR ?= .venv
PY      := $(VENVDIR)/bin/python
PIP     := $(VENVDIR)/bin/pip

.PHONY: venv install dev check lint fmt test
venv:
	@test -d $(VENVDIR) || python3 -m venv $(VENVDIR)

install: venv
	$(PIP) install -r requirements.txt

dev: venv
	$(PIP) install -U pip wheel
	# Ruff-only toolchain
	$(PIP) install ruff

check: lint test
	# Ruff-only checks (lint + format-check)
	$(VENVDIR)/bin/ruff check --output-format=github .
	$(VENVDIR)/bin/ruff format --check .
	$(VENVDIR)/bin/ruff check .
	$(VENVDIR)/bin/ruff format .
	$(VENVDIR)/bin/ruff check --fix .

fmt:
	$(VENVDIR)/bin/black .

test:
	$(VENVDIR)/bin/pytest -q

