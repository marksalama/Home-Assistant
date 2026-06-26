#!/usr/bin/env bash
# One-command installer for the Home Assistant MCP server (macOS / Linux).
# It creates a Python virtual environment, installs the server, and starts the
# friendly setup wizard.
set -e

cd "$(dirname "$0")"

echo "==> Python controleren..."
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is niet gevonden. Installeer Python 3.10+ via https://www.python.org/downloads/ en probeer opnieuw."
  exit 1
fi

echo "==> Virtuele omgeving aanmaken (.venv)..."
python3 -m venv .venv

echo "==> Server installeren..."
./.venv/bin/pip install --quiet --upgrade pip
./.venv/bin/pip install --quiet -e ".[ssh]"

echo "==> Setup-wizard starten..."
exec ./.venv/bin/ha-mcp-setup
