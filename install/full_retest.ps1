# End-to-end install + verify for a clean retest (3050 -> cu130, 5060 -> cu128 nightly).
# Usage:
#   cd K:\tiger\jinFrame\jinFrameComfyUI
#   .\install\full_retest.ps1 -ComfyRoot "K:\ComfyUI\ComfyUI"
#   .\install\full_retest.ps1 -ComfyRoot "K:\ComfyUI\ComfyUI" -SkipSetup   # CUDA + bat only

param(
    [string]$ComfyRoot = $(if ($env:COMFYUI_ROOT) { $env:COMFYUI_ROOT } else { "" }),
    [string]$PythonExe = $(if ($env:JINFRAME_PYTHON) { $env:JINFRAME_PYTHON } else { "" }),
    [switch]$SkipSetup,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "gpu_common.ps1")

$RepoRoot = [System.IO.Path]::GetFullPath((Split-Path $PSScriptRoot -Parent))
if (-not $ComfyRoot) {
    $cfg = Join-Path $RepoRoot "jinframe_install_paths.json"
    if (Test-Path $cfg) {
        $j = Get-Content $cfg -Raw | ConvertFrom-Json
        if ($j.comfy_root) { $ComfyRoot = $j.comfy_root }
    }
}
if (-not $ComfyRoot) { $ComfyRoot = "C:\ComfyUI\ComfyUI" }
$ComfyRoot = [System.IO.Path]::GetFullPath($ComfyRoot)

if (-not $PythonExe) {
    $cfg = Join-Path $RepoRoot "jinframe_install_paths.json"
    if (Test-Path $cfg) {
        $j = Get-Content $cfg -Raw | ConvertFrom-Json
        if ($j.python_home) { $PythonExe = Join-Path $j.python_home "python.exe" }
    }
}
if (-not (Test-Path $PythonExe)) {
    $drive = [System.IO.Path]::GetPathRoot($ComfyRoot)
    $PythonExe = Join-Path $drive "tools\Python312\python.exe"
}
if (-not (Test-Path $PythonExe)) { throw "Python not found. Set -PythonExe or jinframe_install_paths.json" }

function Step([string]$Title) {
    Write-Host ""
    Write-Host "======== $Title ========" -ForegroundColor Cyan
}

Step "1/7 Preflight nvidia-smi"
$smi = Get-SmiGpuInfo
if ($smi.lost) {
    Write-Host "GPU IS LOST - reboot this PC, then re-run full_retest.ps1" -ForegroundColor Red
    exit 2
}
if ($smi.ok) {
    Write-Host "GPU: $($smi.name) driver $($smi.driver)" -ForegroundColor Green
} else {
    Write-Host "No NVIDIA GPU - CPU mode only" -ForegroundColor Yellow
}

Step "2/8 NVIDIA driver check (580+ for cu130)"
& (Join-Path $PSScriptRoot "check_nvidia_driver.ps1") -MinVersion "580.0"
if ($LASTEXITCODE -eq 10) {
    & (Join-Path $PSScriptRoot "install_nvidia_driver.ps1") -RepoRoot $RepoRoot -MinVersion "580.0" -TryElevate
    if ($LASTEXITCODE -eq 5) {
        Set-RebootPending -RepoRoot $RepoRoot -Reason "nvidia_driver_manual" -Detail "Run install\升级NVIDIA驱动(管理员).bat then reboot"
        Write-Host "Driver install needs admin (UAC). Continuing; use 升级NVIDIA驱动 bat after install." -ForegroundColor Yellow
    } elseif ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

Step "3/8 GPU profile"
& (Join-Path $PSScriptRoot "detect_nvidia_gpu.ps1") -RepoRoot $RepoRoot
if ($LASTEXITCODE -eq 2) { exit 2 }

if (-not $SkipSetup) {
    Step "4/8 ComfyUI setup (git + pip + PyTorch + assistant)"
    $setupArgs = @("-ComfyRoot", $ComfyRoot)
    if ($Force) { $setupArgs += "-Force" }
    & (Join-Path $PSScriptRoot "setup_comfyui.ps1") @setupArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Step "4/8 PyTorch CUDA only (-SkipSetup)"
    $pyArgs = @("-PythonExe", $PythonExe, "-RepoRoot", $RepoRoot)
    if ($Force) { $pyArgs += "-Force" }
    & (Join-Path $PSScriptRoot "install_pytorch_cuda.ps1") @pyArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Step "5/8 Sync extension to ComfyUI"
$sync = Join-Path $PSScriptRoot "sync_to_comfyui.ps1"
if (Test-Path $sync) {
    $env:COMFYUI_ROOT = $ComfyRoot
    $env:JINFRAME_REPO_ROOT = $RepoRoot
    & $sync -ComfyRoot $ComfyRoot
}

Step "6/8 Launch bat + CUDA diagnose"
& (Join-Path $PSScriptRoot "write_comfy_launch_bat.ps1") -ComfyRoot $ComfyRoot -RepoRoot $RepoRoot
& (Join-Path $PSScriptRoot "diagnose_cuda.ps1") -PythonExe $PythonExe -RepoRoot $RepoRoot

Step "7/8 Reboot reminder"
& (Join-Path $PSScriptRoot "prompt_reboot_if_needed.ps1") -RepoRoot $RepoRoot

Step "8/8 Done"
$bat = Join-Path $ComfyRoot "启动ComfyUI.bat"
Write-Host ""
Write-Host "Retest checklist:" -ForegroundColor Green
Write-Host "  1. Double-click: $bat"
Write-Host "  2. Browser Ctrl+F5 -> blue chat button on right"
Write-Host "  3. torch on 3050 must show 2.10.0+cu130 (NOT +cu128)"
Write-Host ""
Write-Host "Do NOT run: pip install -r requirements.txt alone (overwrites CUDA torch)" -ForegroundColor Yellow
