# One-command installer for the Home Assistant MCP server (Windows PowerShell).
# Run from PowerShell:  ./install.ps1
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "==> Python controleren..."
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
  Write-Host "Python is niet gevonden. Installeer Python 3.10+ via https://www.python.org/downloads/ en probeer opnieuw."
  exit 1
}

Write-Host "==> Virtuele omgeving aanmaken (.venv)..."
python -m venv .venv

Write-Host "==> Server installeren..."
.\.venv\Scripts\pip.exe install --quiet --upgrade pip
.\.venv\Scripts\pip.exe install --quiet -e ".[ssh]"

Write-Host "==> Setup-wizard starten..."
.\.venv\Scripts\ha-mcp-setup.exe
