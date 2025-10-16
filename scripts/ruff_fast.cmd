@echo off
setlocal enableextensions enabledelayedexpansion
cd /d "%~dp0\.."

rem 0) Install uv if missing (fast installer for ruff)
where uv >nul 2>&1
if errorlevel 1 (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "try { irm https://astral.sh/uv/install.ps1 | iex } catch { exit 1 }"
)
set "PATH=%USERPROFILE%\.local\bin;%PATH%"

rem 1) Determine Ruff version from requirements-dev.txt if available; fallback to a stable pin
if not defined RUFF_VERSION (
  if exist requirements-dev.txt (
    for /f "usebackq delims=" %%V in (`powershell -NoProfile -Command "$l=(Get-Content -Raw 'requirements-dev.txt'); if($l -match '(?im)^\s*ruff[^0-9]*([0-9][^\s#]*)'){ $matches[1] }"`) do set "RUFF_VERSION=%%V"
  )
)
if not defined RUFF_VERSION set "RUFF_VERSION=0.6.9"

rem 2) Create or reuse cached venv dedicated to ruff
set "VENV_DIR=.venv-ruff-%RUFF_VERSION%"
if not exist "%VENV_DIR%" (
  uv venv "%VENV_DIR%"
  call "%VENV_DIR%\Scripts\activate"
  uv pip install "ruff==%RUFF_VERSION%" || uv pip install ruff
) else (
  call "%VENV_DIR%\Scripts\activate"
)

rem 3) Find changed Python files versus origin/main (robust fallbacks)
set "BASE="
for /f "usebackq delims=" %%B in (`git merge-base HEAD origin/main 2^>nul`) do set "BASE=%%B"
if not defined BASE (
  for /f "usebackq delims=" %%B in (`git merge-base HEAD main 2^>nul`) do set "BASE=%%B"
)
if not defined BASE set "BASE=HEAD~1"

set "CHANGED="
for /f "usebackq delims=" %%F in (`git diff --name-only "%BASE%"...HEAD -- *.py 2^>nul`) do (
  if not defined CHANGED (set "CHANGED=%%F") else (set "CHANGED=!CHANGED! %%F")
)

rem 4) Run ruff on changed files only (fallback: all). Default to auto-fix; set RUFF_CHECK=1 to disable fixes
set "RUFF_ARGS=check"
if not defined RUFF_CHECK set "RUFF_CHECK=0"
if "%RUFF_CHECK%"=="0" set "RUFF_ARGS=%RUFF_ARGS% --fix"

if defined CHANGED (
  echo 🔍 Ruff on changed files...
  ruff %RUFF_ARGS% %CHANGED%
) else (
  echo 🔍 Ruff on all files...
  ruff %RUFF_ARGS% .
)

echo ✅ Ruff completed
