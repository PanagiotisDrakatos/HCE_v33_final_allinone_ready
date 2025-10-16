@echo off
setlocal enableextensions enabledelayedexpansion
cd /d "%~dp0\.."

rem Ensure uv is installed and on PATH
where uv >nul 2>&1
if errorlevel 1 (
  echo Installing uv...
  powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
)
set "PATH=%USERPROFILE%\.local\bin;%PATH%"

rem Determine Ruff version from requirements-dev.txt if available; fallback to a stable pin
if not defined RUFF_VERSION (
  if exist requirements-dev.txt (
    for /f "usebackq delims=" %%V in (`powershell -NoProfile -Command "$l=(Get-Content -Raw 'requirements-dev.txt'); if($l -match '(?im)^\s*ruff[^0-9]*([0-9][^\s#]*)'){ $matches[1] }"`) do set "RUFF_VERSION=%%V"
  )
)
if not defined RUFF_VERSION set "RUFF_VERSION=0.6.9"
set "VENV_DIR=.venv-ruff-%RUFF_VERSION%"

rem Create or reuse the venv and install Ruff only via uv (cached)
if not exist "%VENV_DIR%" (
  echo Creating venv: %VENV_DIR%
  uv venv "%VENV_DIR%"
  call "%VENV_DIR%\Scripts\activate"
  uv pip install "ruff==%RUFF_VERSION%" || uv pip install ruff
) else (
  call "%VENV_DIR%\Scripts\activate"
)

rem Ensure pip tooling is present (quiet best-effort)
python -m pip install -q --upgrade pip wheel >nul 2>&1

echo ✅ Bootstrapped env (ruff-only): %VENV_DIR%
