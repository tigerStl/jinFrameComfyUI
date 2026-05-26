# Regenerate launch bat with CUDA preflight (ASCII-only for PowerShell 5.1).
# Usage:
#   .\install\write_comfy_launch_bat.ps1 -ComfyRoot "K:\ComfyUI\ComfyUI" -RepoRoot "K:\tiger\jinFrame\jinFrameComfyUI"

param(
    [string]$ComfyRoot = $(if ($env:COMFYUI_ROOT) { $env:COMFYUI_ROOT } else { "C:\ComfyUI\ComfyUI" }),
    [string]$RepoRoot = ""
)

$ErrorActionPreference = "Stop"
if (-not $RepoRoot) {
    $RepoRoot = Split-Path $PSScriptRoot -Parent
}
$ComfyRoot = [System.IO.Path]::GetFullPath($ComfyRoot)
$RepoRoot = [System.IO.Path]::GetFullPath($RepoRoot)
$batPath = Join-Path $ComfyRoot "启动ComfyUI.bat"
$profilePath = Join-Path $RepoRoot "jinframe_gpu_profile.json"
$pathsPath = Join-Path $RepoRoot "jinframe_install_paths.json"

$Py = "python"
if (Test-Path $pathsPath) {
    $cfg = Get-Content $pathsPath -Raw | ConvertFrom-Json
    if ($cfg.python_home) {
        $cand = Join-Path $cfg.python_home "python.exe"
        if (Test-Path $cand) { $Py = $cand }
    }
}
if (-not (Test-Path $Py)) {
    $drive = [System.IO.Path]::GetPathRoot($ComfyRoot)
    $cand = Join-Path $drive "tools\Python312\python.exe"
    if (Test-Path $cand) { $Py = $cand }
}

$launchArgs = "--lowvram --disable-cuda-malloc"
if (Test-Path $profilePath) {
    $prof = Get-Content $profilePath -Raw | ConvertFrom-Json
    if ($prof.comfy_launch_extra) { $launchArgs = $prof.comfy_launch_extra.Trim() }
}
if ($launchArgs -notmatch "disable-cuda-malloc") {
    $launchArgs = "$launchArgs --disable-cuda-malloc".Trim()
}

$pathSet = ""
if (Test-Path $pathsPath) {
    $cfg = Get-Content $pathsPath -Raw | ConvertFrom-Json
    $parts = @()
    if ($cfg.python_home) { $parts += $cfg.python_home }
    if ($cfg.git_home) {
        $gcmd = Join-Path $cfg.git_home "cmd"
        if (Test-Path $gcmd) { $parts += $gcmd }
    }
    if ($cfg.node_home -and (Test-Path $cfg.node_home)) { $parts += $cfg.node_home }
    if ($parts.Count) { $pathSet = ($parts -join ";") + ";" }
}

$probe = Join-Path $PSScriptRoot "probe_torch_cuda.py"
$repairPs = Join-Path $RepoRoot "install\repair_comfyui_cuda.ps1"

$bat = @"
@echo off
chcp 65001 >nul
title JinFrame ComfyUI
cd /d "$ComfyRoot"
set "PYTHONPATH=%CD%"
set "COMFYUI_ROOT=$ComfyRoot"
set "JINFRAME_REPO_ROOT=$RepoRoot"
"@

if ($pathSet) {
    $bat += "`r`nset `"PATH=$pathSet%PATH%`""
}

$bat += @"

if not exist "main.py" (
  echo [ERROR] main.py not found
  pause
  exit /b 1
)

echo === CUDA preflight ===
"$Py" "$probe"
if errorlevel 1 (
  echo.
  echo [ERROR] PyTorch CUDA not ready.
  echo RTX 3050 / 30-40 need cu130. RTX 5060 / 50 need cu128 nightly.
  echo Run:
  echo   powershell -File "$repairPs" -ComfyRoot "$ComfyRoot"
  pause
  exit /b 1
)

echo Starting ComfyUI: $ComfyRoot
echo Args: $launchArgs
"$Py" main.py $launchArgs
set ERR=%ERRORLEVEL%
if %ERR% neq 0 (
  echo ComfyUI exited with code %ERR%
  echo Do NOT run: pip install -r requirements.txt  (overwrites CUDA torch)
)
pause
"@

$utf8bom = New-Object System.Text.UTF8Encoding $true
[System.IO.File]::WriteAllText($batPath, $bat, $utf8bom)
Write-Host "Wrote $batPath" -ForegroundColor Green
Write-Host "Launch: $launchArgs" -ForegroundColor Cyan
