# Show final reboot reminder if install_nvidia_driver deferred restart.
# Usage: .\install\prompt_reboot_if_needed.ps1 -RepoRoot "..."

param(
    [string]$RepoRoot = "",
    [switch]$Quiet
)

if (-not $RepoRoot) {
    $RepoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
}
. (Join-Path $PSScriptRoot "gpu_common.ps1")

$path = Get-RebootPendingFile $RepoRoot
if (-not (Test-Path $path)) { exit 0 }

$info = Get-Content $path -Raw | ConvertFrom-Json
if ($Quiet) { exit 2 }

Write-Host ""
Write-Host "================================================================" -ForegroundColor Red
Write-Host "  REBOOT REQUIRED (do this now before starting ComfyUI)" -ForegroundColor Red
Write-Host "================================================================" -ForegroundColor Red
Write-Host ""
Write-Host "  Reason: $($info.reason)" -ForegroundColor Yellow
if ($info.detail) { Write-Host "  $($info.detail)" -ForegroundColor DarkGray }
Write-Host ""
if ($info.reason -eq "nvidia_driver_manual") {
    Write-Host "  Driver still too old for PyTorch cu130. Do ONE of:" -ForegroundColor Yellow
    Write-Host "    A) Double-click: install\升级NVIDIA驱动(管理员).bat  (click Yes on UAC)" -ForegroundColor White
    Write-Host "    B) https://www.nvidia.com/Download/index.aspx  (RTX 3050, latest Game Ready)" -ForegroundColor White
    Write-Host "  Then reboot, then repair CUDA (step 2 below)." -ForegroundColor Yellow
    Write-Host ""
}
Write-Host "  After reboot:" -ForegroundColor Cyan
Write-Host "    1. nvidia-smi  (driver should be 580+)" -ForegroundColor White
Write-Host "    2. .\install\repair_comfyui_cuda.ps1 -ComfyRoot YOUR_COMFY_PATH" -ForegroundColor White
Write-Host "    3. Double-click 启动ComfyUI.bat" -ForegroundColor White
Write-Host ""
Write-Host "  Optional reboot now:  shutdown /r /t 60  (cancel: shutdown /a)" -ForegroundColor DarkGray
Write-Host ""
exit 2
