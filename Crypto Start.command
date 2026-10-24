#!/bin/bash
# Crypto Trader - start (macOS).
# Creates .venv on first run, installs requirements, starts the app on
# http://127.0.0.1:8890. Runs beside FOREX Trader: different port, different
# data folder (~/Library/Application Support/CryptoTrader), different lock.
set -e
cd "$(dirname "$0")"

PY=""
for cand in python3.13 python3.12 python3.11 python3; do
  if command -v "$cand" >/dev/null 2>&1; then
    if "$cand" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
      PY="$cand"; break
    fi
  fi
done
if [ -z "$PY" ]; then
  echo "Crypto Trader needs Python 3.11 or newer: https://www.python.org/downloads/"
  read -r -p "Press Enter to close." _; exit 1
fi

if [ ! -x ".venv/bin/python" ]; then
  echo "First run: creating .venv with $PY ..."
  "$PY" -m venv .venv
fi
if [ ! -f ".venv/.installed" ] || [ requirements.txt -nt ".venv/.installed" ]; then
  echo "Installing requirements ..."
  .venv/bin/python -m pip install --quiet --upgrade pip
  .venv/bin/python -m pip install --quiet -r requirements.txt
  touch .venv/.installed
fi

exec .venv/bin/python run.py "$@"
