#!/usr/bin/env bash
set -e

python3 -m venv .venv
if [ -f ".venv/Scripts/activate" ]; then
  # Windows (Git Bash / Cygwin)
  source .venv/Scripts/activate
else
  # Linux / macOS / WSL
  source .venv/bin/activate
fi

python -m pip install -U pip wheel
pip install -r requirements.txt -r requirements-dev.txt
