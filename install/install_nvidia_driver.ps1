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
    [switch]$AllowRebootNow,
    [switch]$TryElevate,
    [switch]$NoElevate
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "gpu_common.ps1")

if (-not $RepoRoot) {
    $RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
}

function Write-Log([string]$Msg, [string]$Color = "White") {
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $Msg" -ForegroundColor $Color
}

function Invoke-ElevatedSelf {
    $self = $PSCommandPath
    $argList = @(
        "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$self`"",
        "-RepoRoot", "`"$RepoRoot`"", "-MinVersion", $MinVersion, "-NoElevate"
    )
    if ($Force) { $argList += "-Force" }
    if ($NoInstall) { $argList += "-NoInstall" }
    if ($AllowRebootNow) { $argList += "-AllowRebootNow" }
    Write-Log "UAC prompt: allow administrator to install NVIDIA driver ..." "Yellow"
    try {
        $p = Start-Process -FilePath "powershell.exe" -Verb RunAs -ArgumentList $argList -Wait -PassThru
        return $p.ExitCode
    } catch {
        Write-Log "UAC denied or elevation failed: $_" "Red"
        return 5
    }
}

if (-not (Test-IsAdmin)) {
    if ($TryElevate -and -not $NoElevate) {
        exit (Invoke-ElevatedSelf)
    }
    Write-Log "Administrator required to install NVIDIA driver." "Red"
    Write-Log "Re-run as admin, or: .\install\install_nvidia_driver.ps1 -TryElevate" "Yellow"
    Write-Log "Or double-click: install\升级NVIDIA驱动(管理员).bat" "Yellow"
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

# Use LocalAppData (not C:\Windows\Temp) to avoid NvApp/CEF "Access is denied"
$workRoot = Join-Path $env:LOCALAPPDATA "jinframe\nvidia_driver"
$destDir = Join-Path $workRoot "download"
$extractDir = Join-Path $workRoot "extract_$($latest.Version)"
$logDir = Join-Path $workRoot "logs"
foreach ($d in @($destDir, $logDir)) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
}
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

Write-Log "Installing display driver only (skip NVIDIA App / CEF) ..." "Yellow"
Write-Log "Extract + setup under: $workRoot" "DarkGray"
Write-Log "This may take 5-15 minutes. Do not close the window." "DarkGray"

$scratchTemp = Join-Path $workRoot "temp"
if (Test-Path $scratchTemp) { Remove-Item $scratchTemp -Recurse -Force -ErrorAction SilentlyContinue }
New-Item -ItemType Directory -Path $scratchTemp -Force | Out-Null
$prevTemp = $env:TEMP
$prevTmp = $env:TMP
$env:TEMP = $scratchTemp
$env:TMP = $scratchTemp

try {
    if (Test-Path $extractDir) { Remove-Item $extractDir -Recurse -Force -ErrorAction SilentlyContinue }
    Write-Log "Extracting package ..." "Cyan"
    $ex = Start-Process -FilePath $installer -ArgumentList @("-extract:$extractDir") -Wait -PassThru
    if ($ex.ExitCode -ne 0) {
        Write-Log "Extract exit $($ex.ExitCode); retry extract to $destDir ..." "DarkYellow"
        $extractDir = Join-Path $destDir "extract"
        if (Test-Path $extractDir) { Remove-Item $extractDir -Recurse -Force -ErrorAction SilentlyContinue }
        $ex = Start-Process -FilePath $installer -ArgumentList @("-extract:$extractDir") -Wait -PassThru
    }

    $setupExe = Get-ChildItem -Path $extractDir -Filter "setup.exe" -Recurse -ErrorAction SilentlyContinue |
        Sort-Object { $_.FullName.Length } | Select-Object -First 1
    if (-not $setupExe) {
        Write-Log "setup.exe not found after extract; trying top-level -s -n Display.Driver ..." "Yellow"
        $setupArgs = @("-s", "-n", "Display.Driver")
        if ($AllowRebootNow) { $setupArgs = @("-s", "Display.Driver") }
        $p = Start-Process -FilePath $installer -ArgumentList $setupArgs -Wait -PassThru
        $code = $p.ExitCode
    } else {
        Write-Log "Using: $($setupExe.FullName)" "DarkGray"
        $setupArgs = @("-s", "-n", "Display.Driver", "-log:$logDir", "-loglevel:6")
        if ($AllowRebootNow) { $setupArgs = @("-s", "Display.Driver", "-log:$logDir", "-loglevel:6") }
        $p = Start-Process -FilePath $setupExe.FullName -WorkingDirectory $setupExe.DirectoryName -ArgumentList $setupArgs -Wait -PassThru
        $code = $p.ExitCode
    }
} finally {
    $env:TEMP = $prevTemp
    $env:TMP = $prevTmp
}

Write-Log "Installer exit code: $code" "Cyan"
if ($code -ne 0 -and (Test-Path $logDir)) {
    Write-Log "See logs: $logDir" "DarkGray"
}

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
