@echo off
setlocal enableextensions enabledelayedexpansion
cd /d "%~dp0\.."

rem ====================================================
rem ⚡ Ruff Fast Format (Windows)
rem ====================================================

set "RUFF_VERSION=0.5.7"
set "RUFF_CACHE=.ruff_cache"

rem --- ensure Ruff exists ---
where ruff >nul 2>&1
if errorlevel 1 (
    echo 🚀 Installing Ruff %RUFF_VERSION% ...
    py -m pip install --disable-pip-version-check --no-input "ruff==%RUFF_VERSION%" || (
        python -m pip install --disable-pip-version-check --no-input "ruff==%RUFF_VERSION%"
    )
)

rem --- run Ruff format ---
echo 🔍 Running: ruff format -q .
ruff format -q .

echo ✅ Ruff format complete.
exit /b 0
