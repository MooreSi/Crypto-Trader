@echo off
setlocal
REM Crypto Trader - stop (Windows).
REM Stops ONLY this app: the pid recorded in its own lock file. Never kills by
REM image name and never touches port 8888 or 9000 (FOREX Trader).
set "DATA=%APPDATA%\CryptoTrader"
if defined CRYPTO_TRADER_DATA_DIR set "DATA=%CRYPTO_TRADER_DATA_DIR%"
set "LOCK=%DATA%\crypto_trader.lock"
if not exist "%LOCK%" (
  echo Crypto Trader is not running.
  exit /b 0
)
for /f "usebackq delims=" %%p in (`powershell -NoProfile -Command "try { (Get-Content -Raw '%LOCK%' | ConvertFrom-Json).pid } catch { '' }"`) do set "PID=%%p"
if not defined PID (
  echo Crypto Trader is not running.
  exit /b 0
)
powershell -NoProfile -Command "$p = Get-CimInstance Win32_Process -Filter 'ProcessId=%PID%'; if ($p -and $p.CommandLine -like '*run.py*') { exit 0 } else { exit 1 }"
if errorlevel 1 (
  echo Crypto Trader is not running.
  exit /b 0
)
taskkill /PID %PID% >nul 2>&1
timeout /t 3 /nobreak >nul
taskkill /PID %PID% /F >nul 2>&1
echo Crypto Trader stopped.
