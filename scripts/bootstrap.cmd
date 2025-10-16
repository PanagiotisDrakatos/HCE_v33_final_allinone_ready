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

rem Compute a stable hash from combined requirements to key the venv
set "REQ_HASH="
for /f "usebackq delims=" %%H in (`powershell -NoProfile -Command "$c=''; if(Test-Path 'requirements.txt'){ $c += Get-Content -Raw requirements.txt }; if(Test-Path 'requirements-dev.txt'){ $c += Get-Content -Raw requirements-dev.txt }; $sha=[System.Security.Cryptography.SHA256]::Create(); $bytes=[System.Text.Encoding]::UTF8.GetBytes($c); $h = $sha.ComputeHash($bytes) | ForEach-Object { $_.ToString('x2') }; ($h -join '')"`) do set "REQ_HASH=%%H"
if not defined REQ_HASH set "REQ_HASH=adhoc"
set "VENV_DIR=.venv-%REQ_HASH%"

if not exist "%VENV_DIR%" (
  echo Creating venv: %VENV_DIR%
  uv venv "%VENV_DIR%"
  call "%VENV_DIR%\Scripts\activate"
  if exist requirements.txt (
    if exist requirements-dev.txt (
      uv pip install -r requirements.txt -r requirements-dev.txt
    ) else (
      uv pip install -r requirements.txt
    )
  ) else (
    if exist requirements-dev.txt (
      uv pip install -r requirements-dev.txt
    )
  )
) else (
  call "%VENV_DIR%\Scripts\activate"
)

rem Minimal tooling: Ruff only
python -m pip install -q --upgrade pip wheel >nul 2>&1
pip install -q ruff >nul 2>&1

echo ✅ Bootstrapped env (ruff-ready): %VENV_DIR%
