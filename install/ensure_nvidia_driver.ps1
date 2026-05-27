# Mandatory NVIDIA driver check BEFORE any ComfyUI / PyTorch install.
# Does NOT install drivers. Writes docs/NVIDIA_DRIVER_UPGRADE.*.md and exits if too old.
# Exit: 0 OK | 2 GPU lost | 3 no NVIDIA (CPU skip) | 10 upgrade required
# Usage: .\install\ensure_nvidia_driver.ps1 -RepoRoot "..."

param(
    [string]$RepoRoot = ""
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "gpu_common.ps1")

if (-not $RepoRoot) {
    $RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
}
$RepoRoot = [System.IO.Path]::GetFullPath($RepoRoot)

function Expand-DriverDocTemplate {
    param(
        [string]$TemplatePath,
        [hashtable]$Vars
    )
    $text = Get-Content -Path $TemplatePath -Raw -Encoding UTF8
    foreach ($key in $Vars.Keys) {
        $text = $text.Replace("{{$key}}", [string]$Vars[$key])
    }
    return $text
}

function Write-DriverUpgradeDocs {
    param(
        $Smi,
        [string]$MinVersion,
        [string]$TorchProfile,
        [bool]$Passed
    )

    $docsDir = Join-Path $RepoRoot "docs"
    if (-not (Test-Path $docsDir)) { New-Item -ItemType Directory -Path $docsDir -Force | Out-Null }

    $now = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    $drv = if ($Smi.driver) { $Smi.driver } else { "(none)" }
    $gpu = if ($Smi.name) { $Smi.name } else { "(none)" }

    $statusZh = if ($Passed) { "PASSED" } else { "FAILED - upgrade driver before install" }
    $statusEn = $statusZh

    $latestZh = ""
    $latestEn = ""
    try {
        $latest = Get-LatestGeForceGameReadyDriver
        if ($latest) {
            $latestZh = "NVIDIA site example Game Ready version: **$($latest.Version)** (reference)"
            $latestEn = $latestZh
        }
    } catch { }

    $vars = @{
        CHECKED_AT      = $now
        STATUS          = $statusZh
        GPU_NAME        = $gpu
        DRIVER_VERSION  = $drv
        MIN_VERSION     = $MinVersion
        TORCH_PROFILE   = $TorchProfile
        LATEST_ONLINE   = $latestZh
    }

    $tplZh = Join-Path $PSScriptRoot "templates\NVIDIA_DRIVER_UPGRADE.zh-CN.md"
    $tplEn = Join-Path $PSScriptRoot "templates\NVIDIA_DRIVER_UPGRADE.en.md"
    $outZh = Join-Path $docsDir "NVIDIA_DRIVER_UPGRADE.zh-CN.md"
    $outEn = Join-Path $docsDir "NVIDIA_DRIVER_UPGRADE.en.md"

    $varsEn = $vars.Clone()
    $varsEn["LATEST_ONLINE"] = $latestEn
    $varsEn["STATUS"] = $statusEn

    Set-Content -Path $outZh -Value (Expand-DriverDocTemplate -TemplatePath $tplZh -Vars $vars) -Encoding UTF8
    Set-Content -Path $outEn -Value (Expand-DriverDocTemplate -TemplatePath $tplEn -Vars $varsEn) -Encoding UTF8
    return @{ Zh = $outZh; En = $outEn }
}

Write-Host ""
Write-Host "=== NVIDIA driver pre-check (required before install) ===" -ForegroundColor Cyan

$smi = Get-SmiGpuInfo
if ($smi.lost) {
    Write-Host "[driver] GPU IS LOST - reboot PC, then re-run ensure_nvidia_driver.ps1" -ForegroundColor Red
    exit 2
}

if (-not $smi.ok) {
    Write-Host "[driver] No NVIDIA GPU - CPU-only mode (skip driver requirement)" -ForegroundColor Yellow
    exit 0
}

$profile = New-GpuProfileObject -GpuName $smi.name -Driver $smi.driver
$minVer = switch ($profile.torch_profile) {
    "cu128_nightly" { "570.0" }
    "cu130" { "580.0" }
    default { "580.0" }
}

$ok = Test-DriverForTorchProfile $smi.driver $profile.torch_profile
$paths = Write-DriverUpgradeDocs -Smi $smi -MinVersion $minVer -TorchProfile $profile.torch_profile -Passed $ok

Write-Host "[driver] GPU: $($smi.name)" -ForegroundColor Cyan
Write-Host "[driver] Installed: $($smi.driver) | Required: >= $minVer ($($profile.torch_profile))" -ForegroundColor Cyan
Write-Host "[driver] Docs: $($paths.Zh)" -ForegroundColor DarkGray
Write-Host "[driver]       $($paths.En)" -ForegroundColor DarkGray

if ($ok) {
    Write-Host "[driver] OK - continuing install" -ForegroundColor Green
    exit 0
}

Write-Host ""
Write-Host "================================================================" -ForegroundColor Red
Write-Host "  INSTALL STOPPED: upgrade NVIDIA driver first (manual)" -ForegroundColor Red
Write-Host "================================================================" -ForegroundColor Red
Write-Host ""
Write-Host "  Current: $($smi.driver)  |  Required: >= $minVer" -ForegroundColor Yellow
Write-Host "  Read:    docs\NVIDIA_DRIVER_UPGRADE.zh-CN.md" -ForegroundColor White
Write-Host "           docs\NVIDIA_DRIVER_UPGRADE.en.md" -ForegroundColor White
Write-Host ""
Write-Host "  After upgrade + reboot, run ensure_nvidia_driver.ps1 again." -ForegroundColor Cyan
Write-Host ""
exit 10
