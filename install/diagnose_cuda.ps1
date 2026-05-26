# Print CUDA / PyTorch / driver info for troubleshooting ComfyUI startup.
param(
    [string]$PythonExe = "",
    [string]$RepoRoot = ""
)

if (-not $RepoRoot) { $RepoRoot = Split-Path $PSScriptRoot -Parent }
$RepoRoot = [System.IO.Path]::GetFullPath($RepoRoot)

if (-not $PythonExe) {
    $cfg = Join-Path $RepoRoot "jinframe_install_paths.json"
    if (Test-Path $cfg) {
        $j = Get-Content $cfg -Raw | ConvertFrom-Json
        if ($j.python_home) { $PythonExe = Join-Path $j.python_home "python.exe" }
    }
}
if (-not (Test-Path $PythonExe)) { $PythonExe = "python" }

Write-Host "=== JinFrame CUDA diagnose ===" -ForegroundColor Cyan
Write-Host "Python: $PythonExe"
Write-Host "Repo:   $RepoRoot"
Write-Host ""

Write-Host "--- nvidia-smi ---" -ForegroundColor Yellow
$smiOk = $false
if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
    $smiOut = & nvidia-smi 2>&1 | Out-String
    Write-Host $smiOut
    if ($smiOut -match "GPU is lost|Unable to determine the device handle") {
        Write-Host ""
        Write-Host "[CRITICAL] NVIDIA driver reports GPU IS LOST (not a PyTorch bug)." -ForegroundColor Red
        Write-Host "  1. Reboot the 3050 PC (required before any pip / ComfyUI fix)." -ForegroundColor Yellow
        Write-Host "  2. After reboot, run: nvidia-smi  (must show RTX 3050 normally)" -ForegroundColor Yellow
        Write-Host "  3. Then: git pull + repair_comfyui_cuda.ps1" -ForegroundColor Yellow
        Write-Host "Remote Desktop is OK; GPU must be healthy in nvidia-smi first." -ForegroundColor DarkGray
    } elseif ($LASTEXITCODE -eq 0 -and $smiOut -match "RTX|GeForce|NVIDIA") {
        $smiOk = $true
    }
} else {
    Write-Host "nvidia-smi NOT FOUND" -ForegroundColor Red
}

Write-Host ""
Write-Host "--- torch ---" -ForegroundColor Yellow
& $PythonExe -c @"
import torch
print('version:', torch.__version__)
print('cuda build:', getattr(torch.version, 'cuda', None))
print('is_available:', torch.cuda.is_available())
try:
    d = torch.cuda.current_device()
    print('current_device:', d, torch.cuda.get_device_name(d))
except Exception as e:
    print('current_device FAILED:', e)
"@

Write-Host ""
Write-Host "--- probe (ComfyUI-style) ---" -ForegroundColor Yellow
$env:JINFRAME_REPO_ROOT = $RepoRoot
& $PythonExe (Join-Path $PSScriptRoot "probe_torch_cuda.py")
Write-Host "probe exit: $LASTEXITCODE"

$p = Join-Path $RepoRoot "jinframe_gpu_profile.json"
if (Test-Path $p) {
    Write-Host ""
    Write-Host "--- jinframe_gpu_profile.json ---" -ForegroundColor Yellow
    Get-Content $p
}
