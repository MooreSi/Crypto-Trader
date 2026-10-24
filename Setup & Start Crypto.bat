@echo off
setlocal
REM Crypto Trader - setup and start (Windows).
REM Creates .venv on first run, installs requirements, starts the app on
REM http://127.0.0.1:8890. Runs beside FOREX Trader: different port, data
REM folder (%APPDATA%\CryptoTrader) and lock.
cd /d "%~dp0"

set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY where python >nul 2>&1 && set "PY=python"
if not defined PY (
  echo Crypto Trader needs Python 3.11 or newer: https://www.python.org/downloads/
  pause
  exit /b 1
)
%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"
if errorlevel 1 (
  echo Crypto Trader needs Python 3.11 or newer.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo First run: creating .venv ...
  %PY% -m venv .venv
)
if not exist ".venv\.installed" (
  echo Installing requirements ...
  ".venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
  ".venv\Scripts\python.exe" -m pip install --quiet -r requirements.txt
  if errorlevel 1 ( pause & exit /b 1 )
  type nul > ".venv\.installed"
)

".venv\Scripts\python.exe" run.py %*
if errorlevel 1 pause
