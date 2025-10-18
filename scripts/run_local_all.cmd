@echo off
setlocal enabledelayedexpansion

echo == Python env ==
python -V
pip --version

REM Lint checks (Ruff-only)
echo == Ruff check ==
ruff check .
if errorlevel 1 goto :end

REM Unit tests (pytest.ini excludes integration by default)
echo == Unit tests ==
pytest -q
if errorlevel 1 goto :end

REM Integration tests (will succeed only if DBs are up)
echo == Integration tests ==
pytest -q -m integration
REM Do not fail the script if integration tests fail locally

:end
endlocal
