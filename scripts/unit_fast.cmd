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

rem Only Ruff linting
echo 🔍 Linting (ruff)...
ruff check --select I,E,F,UP .
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo Ruff reported issues (exit %RC%).
)
exit /b %RC%
