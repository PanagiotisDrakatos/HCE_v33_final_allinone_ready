VENVDIR ?= .venv
PY      := $(VENVDIR)/bin/python
PIP     := $(VENVDIR)/bin/pip

.PHONY: venv install dev check lint fmt test
venv:
	@test -d $(VENVDIR) || python3 -m venv $(VENVDIR)

install: venv
	$(PIP) install -r requirements.txt

dev: venv
	$(PIP) install pylint==2.17.4 ruff black

check: lint test

lint:
	$(VENVDIR)/bin/ruff check .
	$(VENVDIR)/bin/pylint hcebt || true

fmt:
	$(VENVDIR)/bin/black .

test:
	$(VENVDIR)/bin/pytest -q

