# One-command installer for the Home Assistant MCP server (Windows PowerShell).
# Run from PowerShell:  ./install.ps1
$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "==> Python controleren..."
$python = Get-Command python -ErrorAction SilentlyContinue
$pythonArgs = @()
if ($python) {
  $pythonExe = $python.Source
} else {
  $py = Get-Command py -ErrorAction SilentlyContinue
  if ($py) {
    $pythonExe = $py.Source
    $pythonArgs = @("-3")
  }
}
if (-not $pythonExe) {
  Write-Host "Python is niet gevonden. Installeer Python 3.10+ via https://www.python.org/downloads/ en probeer opnieuw."
  exit 1
}
& $pythonExe @pythonArgs -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
if ($LASTEXITCODE -ne 0) {
  Write-Host "Python 3.10 of nieuwer is nodig. Installeer een nieuwere versie en probeer opnieuw."
  exit 1
}

Write-Host "==> Virtuele omgeving aanmaken (.venv)..."
& $pythonExe @pythonArgs -m venv .venv

Write-Host "==> Server installeren..."
.\.venv\Scripts\pip.exe install --quiet --upgrade pip
.\.venv\Scripts\pip.exe install --quiet -e ".[ssh]"

Write-Host "==> Setup-wizard starten..."
.\.venv\Scripts\ha-mcp-setup.exe
