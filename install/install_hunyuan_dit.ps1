# Hunyuan DiT 1.2 — download pinned revision from MODELS.lock.json
# Run from jinFrameComfyUI repo root:
#   .\install\install_hunyuan_dit.ps1
#   .\install\install_hunyuan_dit.ps1 -ComfyRoot "D:\ComfyUI\ComfyUI"

param(
    [string]$ComfyRoot = $(if ($env:COMFYUI_ROOT) { $env:COMFYUI_ROOT } else { "C:\ComfyUI\ComfyUI" })
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
$Python = if ($env:JINFRAME_PYTHON) { $env:JINFRAME_PYTHON } else { "python" }

$env:COMFYUI_ROOT = $ComfyRoot
Set-Location $RepoRoot
& $Python install\download_from_lock.py --pack hunyuan_dit
if ($LASTEXITCODE -ne 0) { throw "download_from_lock failed" }
& $Python install\verify_models.py --pack hunyuan_dit
if ($LASTEXITCODE -ne 0) { throw "verify_models failed" }

Write-Host "`nLoad workflow: user\default\workflows\HunyuanDiT_T2I_中国风格.json" -ForegroundColor Cyan
Write-Host "8GB tip: run ComfyUI with --lowvram --cpu-vae" -ForegroundColor Cyan
