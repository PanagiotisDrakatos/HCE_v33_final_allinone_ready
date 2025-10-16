@echo off
setlocal enableextensions enabledelayedexpansion
cd /d "%~dp0\.."

rem Find latest hashed venv
set "VENV_DIR="
for /f "tokens=*" %%D in ('dir /ad /b /o:-d .venv-* 2^>nul') do (
  set "VENV_DIR=%%D"
  goto :found
)
:found
if not defined VENV_DIR (
  echo ❌ No venv found. Run scripts\bootstrap.cmd first.
  exit /b 1
)
call "%VENV_DIR%\Scripts\activate"

set PYTEST_DISABLE_PLUGIN_AUTOLOAD=1

echo 🔍 Linting (ruff/black)...
ruff check --select I,E,F,UP .
if errorlevel 1 (
  echo Ruff reported issues.
)
black --check .
if errorlevel 1 (
  echo Black check failed. You can auto-format with: black .
)

echo ⚙️  Running fast unit tests...
pytest -q -m "not integration" -n auto --cov=hcebt --cov=lib --cov-report=xml
exit /b %errorlevel%

