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

Write-Host "Installed. Restart ComfyUI completely." -ForegroundColor Green
Write-Host @"

After restart:
  - Right edge: blue chat button
  - Missing models: checkboxes at top -> [One-click download]
  - Chat: needs Ollama + Qwen (default):
      ollama pull qwen2.5:7b

Optional env:
  OLLAMA_HOST=http://127.0.0.1:11434
  COMFYUI_ROOT=$ComfyRoot
"@ -ForegroundColor Cyan
