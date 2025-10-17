VENVDIR ?= .venv
PY      := $(VENVDIR)/bin/python
PIP     := $(VENVDIR)/bin/pip

.PHONY: venv install dev check lint fmt autofix test

venv:
	@test -d $(VENVDIR) || python3 -m venv $(VENVDIR)

install: venv
	$(PIP) install -r requirements.txt
	$(PIP) install -e .

dev: install
	$(PIP) install -r requirements-dev.txt

# Run lint then tests
check: lint test

# Lint with ruff only (flake8/isort replaced)
lint: dev
	$(VENVDIR)/bin/ruff check .

# Format using ruff format (black replaced)
fmt: dev
	$(VENVDIR)/bin/ruff format .

# Auto-fix: ruff check --fix then ruff format
autofix: dev
	$(VENVDIR)/bin/ruff check . --fix
	$(VENVDIR)/bin/ruff format .

# Run test suite (exclude integration tests directory to avoid imports)
test: dev
	$(VENVDIR)/bin/pytest -q --ignore=tests/integration
