# Wrapper: use ensure_nvidia_driver.ps1 (check only, same exit codes).
# Usage: .\install\check_nvidia_driver.ps1

param(
    [string]$MinVersion = "",
    [switch]$ShowLatestOnline
)

$repo = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
& (Join-Path $PSScriptRoot "ensure_nvidia_driver.ps1") -RepoRoot $repo
exit $LASTEXITCODE
