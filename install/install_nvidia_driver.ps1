# Download and install latest GeForce Game Ready driver; defer reboot until end (-n).
# Requires Administrator. Writes jinframe_reboot_pending.json when reboot is needed.
# Usage:
#   .\install\install_nvidia_driver.ps1
#   .\install\install_nvidia_driver.ps1 -MinVersion 580.0 -RepoRoot "K:\tiger\jinFrame\jinFrameComfyUI"

param(
    [string]$RepoRoot = "",
    [string]$MinVersion = "580.0",
    [switch]$Force,
    [switch]$NoInstall,
    [switch]$AllowRebootNow
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "gpu_common.ps1")

if (-not $RepoRoot) {
    $RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
}

function Write-Log([string]$Msg, [string]$Color = "White") {
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $Msg" -ForegroundColor $Color
}

if (-not (Test-IsAdmin)) {
    Write-Log "Administrator required to install NVIDIA driver." "Red"
    Write-Log "Right-click PowerShell -> Run as administrator, then re-run this script." "Yellow"
    exit 5
}

$smi = Get-SmiGpuInfo
if ($smi.lost) {
    Write-Log "GPU IS LOST. Reboot PC first, then run this script again." "Red"
    exit 2
}
if (-not $smi.ok) {
    Write-Log "No NVIDIA GPU - skip driver install" "Yellow"
    exit 0
}

Write-Log "GPU: $($smi.name)" "Cyan"
Write-Log "Current driver: $($smi.driver)" "Cyan"

if (-not $Force -and (Test-NvidiaDriverVersion $smi.driver $MinVersion)) {
    Write-Log "Driver already >= $MinVersion - no install needed" "Green"
    exit 0
}

Write-Log "Fetching latest GeForce Game Ready driver from NVIDIA ..." "Cyan"
$latest = Get-LatestGeForceGameReadyDriver
if (-not $latest) {
    Write-Log "Could not query NVIDIA download page" "Red"
    exit 4
}
Write-Log "Latest online: $($latest.Version)" "Green"

if (-not $Force -and $smi.driver) {
    try {
        if ([version]$smi.driver -ge [version]$latest.Version) {
            Write-Log "Installed driver is already latest ($($smi.driver))" "Green"
            if (-not (Test-NvidiaDriverVersion $smi.driver $MinVersion)) {
                Write-Log "But still below $MinVersion - unusual; try -Force or manual install" "Yellow"
                exit 10
            }
            exit 0
        }
    } catch { }
}

$destDir = Join-Path $env:TEMP "jinframe_nvidia_driver"
if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Path $destDir | Out-Null }
$installer = Join-Path $destDir "GeForce_$($latest.Version)-win11-dch-whql.exe"

Write-Log "Download (~900MB): $($latest.DownloadUrl)" "Cyan"
Write-Log "Saving to: $installer" "DarkGray"
if (-not $NoInstall) {
    Invoke-WebRequest -Uri $latest.DownloadUrl -OutFile $installer -UseBasicParsing
}

if ($NoInstall) {
    Write-Log "NoInstall: downloaded only" "Yellow"
    exit 0
}

Write-Log "Installing driver silently (no reboot yet: -s -n) ..." "Yellow"
Write-Log "This may take 5-15 minutes. Do not close the window." "DarkGray"

$args = @("-s", "-n")
if ($AllowRebootNow) {
    $args = @("-s")
    Write-Log "AllowRebootNow: installer may reboot immediately" "Yellow"
}

$p = Start-Process -FilePath $installer -ArgumentList $args -Wait -PassThru
$code = $p.ExitCode
Write-Log "Installer exit code: $code" "Cyan"

# NVIDIA: 0 = success, 1 = success reboot required
if ($code -eq 0 -or $code -eq 1) {
    if ($AllowRebootNow -and $code -eq 1) {
        Write-Log "Driver installed. System may reboot now." "Green"
        Clear-RebootPending $RepoRoot
    } else {
        Set-RebootPending -RepoRoot $RepoRoot -Reason "nvidia_driver" -Detail "Installed GeForce $($latest.Version). Reboot before CUDA/ComfyUI."
        Write-Log "Driver installed (pending reboot). CUDA will not work until you restart." "Green"
        Write-Log "Continue other install steps; reboot at the very end." "Yellow"
    }
    exit 0
}

Write-Log "Driver installer failed with exit code $code" "Red"
Write-Log "Try manual install from: $($latest.DownloadUrl)" "Yellow"
exit 1
