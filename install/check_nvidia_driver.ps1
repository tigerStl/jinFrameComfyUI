# Check NVIDIA driver vs JinFrame / PyTorch requirements.
# Exit: 0 OK | 10 upgrade needed | 2 GPU lost | 3 no NVIDIA
# Usage: .\install\check_nvidia_driver.ps1 -MinVersion 580.0

param(
    [string]$MinVersion = "580.0",
    [switch]$ShowLatestOnline
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "gpu_common.ps1")

$smi = Get-SmiGpuInfo
if ($smi.lost) {
    Write-Host "[driver] GPU IS LOST - reboot required" -ForegroundColor Red
    exit 2
}
if (-not $smi.ok) {
    Write-Host "[driver] No NVIDIA GPU detected" -ForegroundColor Yellow
    exit 3
}

Write-Host "[driver] GPU: $($smi.name)" -ForegroundColor Cyan
Write-Host "[driver] Installed: $($smi.driver)" -ForegroundColor Cyan

$ok = Test-NvidiaDriverVersion $smi.driver $MinVersion
if ($ok) {
    Write-Host "[driver] OK (>= $MinVersion for PyTorch cu130)" -ForegroundColor Green
} else {
    Write-Host "[driver] NEED UPGRADE: $($smi.driver) < $MinVersion" -ForegroundColor Red
    Write-Host "[driver] Run: .\install\install_nvidia_driver.ps1" -ForegroundColor Yellow
}

if ($ShowLatestOnline) {
    Write-Host "[driver] Querying NVIDIA for latest Game Ready driver ..." -ForegroundColor DarkGray
    $latest = Get-LatestGeForceGameReadyDriver
    if ($latest) {
        Write-Host "[driver] Latest online: $($latest.Version)" -ForegroundColor Green
        Write-Host "[driver] URL: $($latest.DownloadUrl)" -ForegroundColor DarkGray
    }
}

if ($ok) { exit 0 }
exit 10
