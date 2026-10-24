#!/bin/bash
# Crypto Trader - stop (macOS).
# Stops ONLY this app: the pid recorded in its own lock file, checked to be a
# Python process running run.py before it is signalled. Never kills by name
# and never touches port 8888 (FOREX Trader).
DATA_DIR="${CRYPTO_TRADER_DATA_DIR:-$HOME/Library/Application Support/${CRYPTO_TRADER_DATA_DIR_NAME:-CryptoTrader}}"
LOCK="$DATA_DIR/crypto_trader.lock"
if [ ! -f "$LOCK" ]; then
  echo "Crypto Trader is not running (no lock file)."; exit 0
fi
PID=$(/usr/bin/python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("pid",""))' "$LOCK" 2>/dev/null)
if [ -z "$PID" ] || ! ps -p "$PID" >/dev/null 2>&1; then
  echo "Crypto Trader is not running."; exit 0
fi
if ! ps -p "$PID" -o command= | grep -q "run.py"; then
  echo "pid $PID is not Crypto Trader; leaving it alone."; exit 1
fi
kill -TERM "$PID"
for _ in $(seq 1 20); do
  ps -p "$PID" >/dev/null 2>&1 || { echo "Crypto Trader stopped."; exit 0; }
  sleep 0.5
done
echo "Crypto Trader (pid $PID) did not stop within 10s."; exit 1
