# Install JinFrame Assistant into ComfyUI custom_nodes (chat UI + model download).
# Usage: .\install\install_jinframe_assistant.ps1
#        .\install\install_jinframe_assistant.ps1 -ComfyRoot "D:\ComfyUI\ComfyUI"

param(
    [string]$ComfyRoot = $(if ($env:COMFYUI_ROOT) { $env:COMFYUI_ROOT } else { "C:\ComfyUI\ComfyUI" })
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
$Src = Join-Path $RepoRoot "comfyui_extension\ComfyUI_JinFrameAssistant"
$Dst = Join-Path $ComfyRoot "custom_nodes\ComfyUI_JinFrameAssistant"

if (-not (Test-Path $Src)) {
    throw "Missing extension source: $Src"
}

Write-Host "=== JinFrame Assistant -> ComfyUI ===" -ForegroundColor Cyan
Write-Host "Src: $Src"
Write-Host "Dst: $Dst"

if (Test-Path $Dst) {
    Remove-Item $Dst -Recurse -Force
}
New-Item -ItemType Directory -Force -Path (Split-Path $Dst) | Out-Null
Copy-Item -Recurse -Force $Src $Dst

$Python = Join-Path (Split-Path $ComfyRoot -Parent) "python_embeded\python.exe"
if (-not (Test-Path $Python)) {
    $Python = "python"
}
Write-Host "[pip] cursor-sdk (Cursor Agent)" -ForegroundColor Green
& $Python -m pip install -r (Join-Path $Dst "requirements.txt") -q

Write-Host "Installed. Restart ComfyUI completely." -ForegroundColor Green
Write-Host @"

After restart:
  - Right edge: blue chat button
  - Top: [x] Cursor Agent + paste API Key + Save
  - Agent ON: edits workflows/ via Cursor SDK (local repo)
  - Agent OFF: chat uses Ollama Qwen (ollama pull qwen2.5:7b)
  - Models: checkboxes -> [One-click download]

Set repo for Agent (path to this git clone):
  `$env:JINFRAME_REPO_ROOT = "<path-to-jinFrameComfyUI>"`

Optional env:
  OLLAMA_HOST=http://127.0.0.1:11434
  COMFYUI_ROOT=$ComfyRoot
"@ -ForegroundColor Cyan
