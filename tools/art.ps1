# Art pipeline wrapper. Usage: tools\art.ps1 build [recipe] | validate | new <name> | list | palette [list|inspect <name>]
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { & (Join-Path $PSScriptRoot "setup.ps1") }
& $py (Join-Path $PSScriptRoot "art\artkit.py") @args
exit $LASTEXITCODE
