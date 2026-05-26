# Re-detect GPU and install matching PyTorch (3050->cu130, 5060->cu128 nightly).
# Usage:
#   .\install\repair_comfyui_cuda.ps1 -ComfyRoot "K:\ComfyUI\ComfyUI"

param(
    [string]$ComfyRoot = $(if ($env:COMFYUI_ROOT) { $env:COMFYUI_ROOT } else { "C:\ComfyUI\ComfyUI" }),
    [string]$RepoRoot = ""
)

$ErrorActionPreference = "Stop"
if (-not $RepoRoot) {
    $RepoRoot = Split-Path $PSScriptRoot -Parent
}
$RepoRoot = [System.IO.Path]::GetFullPath($RepoRoot)
$ComfyRoot = [System.IO.Path]::GetFullPath($ComfyRoot)

$Py = $env:JINFRAME_PYTHON
if (-not ($Py -and (Test-Path $Py))) {
    $cfg = Join-Path $RepoRoot "jinframe_install_paths.json"
    if (Test-Path $cfg) {
        $j = Get-Content $cfg -Raw | ConvertFrom-Json
        if ($j.python_home) { $Py = Join-Path $j.python_home "python.exe" }
    }
}
if (-not (Test-Path $Py)) {
    $drive = [System.IO.Path]::GetPathRoot($ComfyRoot)
    $Py = Join-Path $drive "tools\Python312\python.exe"
}
if (-not (Test-Path $Py)) { throw "Python not found at $Py" }

Write-Host "=== Repair CUDA PyTorch (auto GPU profile) ===" -ForegroundColor Cyan
Write-Host "Python: $Py"
Write-Host "Comfy:  $ComfyRoot"

& (Join-Path $PSScriptRoot "detect_nvidia_gpu.ps1") -RepoRoot $RepoRoot
& (Join-Path $PSScriptRoot "install_pytorch_cuda.ps1") -PythonExe $Py -RepoRoot $RepoRoot
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& (Join-Path $PSScriptRoot "write_comfy_launch_bat.ps1") -ComfyRoot $ComfyRoot -RepoRoot $RepoRoot

$profile = Get-Content (Join-Path $RepoRoot "jinframe_gpu_profile.json") -Raw | ConvertFrom-Json
Write-Host ""
Write-Host "Profile: $($profile.torch_profile)" -ForegroundColor Green
Write-Host "Launch:  python main.py $($profile.comfy_launch_extra)" -ForegroundColor Green
Write-Host ""
Write-Host "Re-run one-click install OR edit 启动ComfyUI.bat to use launch args above." -ForegroundColor Yellow
& $Py (Join-Path $PSScriptRoot "probe_torch_cuda.py")
