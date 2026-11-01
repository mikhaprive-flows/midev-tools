# Standalone Python venv setup for midev art tools
$ErrorActionPreference = "Stop"
$venv = Join-Path $PSScriptRoot ".venv"
if (-not (Test-Path "$venv\Scripts\python.exe")) {
    Write-Host "[setup] Creating virtual environment at $venv..."
    python -m venv $venv
}
Write-Host "[setup] Installing/verifying dependencies..."
& "$venv\Scripts\python.exe" -m pip install -q -r (Join-Path $PSScriptRoot "requirements.txt")
Write-Host "[setup] Environment ready."
