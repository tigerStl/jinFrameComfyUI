# Sync jinFrameComfyUI -> local ComfyUI (workflows + optional distill LoRA).
# Usage:
#   .\install\sync_to_comfyui.ps1
#   .\install\sync_to_comfyui.ps1 -ComfyRoot "D:\ComfyUI\ComfyUI"
#   .\install\sync_to_comfyui.ps1 -WorkflowsOnly

param(
    [string]$ComfyRoot = $(if ($env:COMFYUI_ROOT) { $env:COMFYUI_ROOT } else { "C:\ComfyUI\ComfyUI" }),
    [switch]$WorkflowsOnly,
    [switch]$DistillLora
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
$WfSrc = Join-Path $RepoRoot "workflows"
$WfDst = Join-Path $ComfyRoot "user\default\workflows"

if (-not (Test-Path $WfSrc)) {
    throw "Missing workflows: $WfSrc"
}

Write-Host "=== jinFrameComfyUI -> ComfyUI ===" -ForegroundColor Cyan
Write-Host "Repo:  $RepoRoot"
Write-Host "Comfy: $ComfyRoot"

New-Item -ItemType Directory -Force -Path $WfDst | Out-Null
Write-Host "[sync] workflows -> $WfDst" -ForegroundColor Green
robocopy $WfSrc $WfDst /E /NFL /NDL /NJH /NJS /R:1 /W:1 | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy workflows failed: $LASTEXITCODE" }

if (-not $WorkflowsOnly) {
    $LoraSrc = Join-Path $RepoRoot "distill_loras"
    $LoraName = "ltx-2.3-22b-distilled-lora-1.1_fro90_ceil72_condsafe.safetensors"
    $LoraFile = Join-Path $LoraSrc $LoraName
    if (Test-Path $LoraFile) {
        $LoraDstDir = Join-Path $ComfyRoot "models\loras"
        New-Item -ItemType Directory -Force -Path $LoraDstDir | Out-Null
        $LoraDst = Join-Path $LoraDstDir $LoraName
        if ($DistillLora -or -not (Test-Path $LoraDst)) {
            Copy-Item -Force $LoraFile $LoraDst
            Write-Host "[sync] distill LoRA -> $LoraDst" -ForegroundColor Green
        }
    }
}

Write-Host "Done. Restart ComfyUI if workflows were open." -ForegroundColor Cyan
