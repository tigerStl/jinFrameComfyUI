# Install JinFrame Assistant into ComfyUI custom_nodes (chat UI + model download).
# Usage: .\install\install_jinframe_assistant.ps1
#        .\install\install_jinframe_assistant.ps1 -ComfyRoot "K:\ComfyUI\ComfyUI"

param(
    [string]$ComfyRoot = $(if ($env:COMFYUI_ROOT) { $env:COMFYUI_ROOT } else { "C:\ComfyUI\ComfyUI" })
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
$Src = Join-Path $RepoRoot "comfyui_extension\ComfyUI_JinFrameAssistant"
$Dst = Join-Path $ComfyRoot "custom_nodes\ComfyUI_JinFrameAssistant"

function Resolve-PythonForAssistant {
    param([string]$ComfyRootPath)
    if ($env:JINFRAME_PYTHON -and (Test-Path $env:JINFRAME_PYTHON)) {
        return $env:JINFRAME_PYTHON
    }
    $pathsFile = Join-Path $RepoRoot "jinframe_install_paths.json"
    if (Test-Path $pathsFile) {
        try {
            $cfg = Get-Content $pathsFile -Raw | ConvertFrom-Json
            if ($cfg.python_home) {
                $py = Join-Path $cfg.python_home "python.exe"
                if (Test-Path $py) { return $py }
            }
        } catch { }
    }
    $driveRoot = [System.IO.Path]::GetPathRoot($ComfyRootPath)
    if ($driveRoot) {
        $toolsPy = Join-Path $driveRoot "tools\Python312\python.exe"
        if (Test-Path $toolsPy) { return $toolsPy }
    }
    $emb = Join-Path (Split-Path $ComfyRootPath -Parent) "python_embeded\python.exe"
    if (Test-Path $emb) { return $emb }
    return "python"
}

if (-not (Test-Path $Src)) {
    throw "Missing extension source: $Src"
}

$ComfyRoot = [System.IO.Path]::GetFullPath($ComfyRoot)
if (-not (Test-Path (Join-Path $ComfyRoot "main.py"))) {
    throw "ComfyUI not found at $ComfyRoot (no main.py). Run setup_comfyui.ps1 first."
}

Write-Host "=== JinFrame Assistant -> ComfyUI ===" -ForegroundColor Cyan
Write-Host "Src: $Src"
Write-Host "Dst: $Dst"
Write-Host "Repo: $RepoRoot"

if (Test-Path $Dst) {
    Remove-Item $Dst -Recurse -Force
}
New-Item -ItemType Directory -Force -Path (Split-Path $Dst) | Out-Null
Copy-Item -Recurse -Force $Src $Dst

if (-not (Test-Path (Join-Path $Dst "__init__.py"))) {
    throw "Copy failed: missing $Dst\__init__.py"
}

$Python = Resolve-PythonForAssistant -ComfyRootPath $ComfyRoot
Write-Host "[pip] cursor-sdk (Cursor Agent) via $Python" -ForegroundColor Green
$prevEa = $ErrorActionPreference
$ErrorActionPreference = "Continue"
try {
    $p = Start-Process -FilePath $Python -ArgumentList @(
        "-m", "pip", "install", "-r", (Join-Path $Dst "requirements.txt"), "-q"
    ) -Wait -PassThru -NoNewWindow
    if ($p.ExitCode -ne 0) {
        Write-Host "[warn] pip install cursor-sdk exit $($p.ExitCode) - Agent mode may be unavailable until fixed" -ForegroundColor Yellow
    }
} finally {
    $ErrorActionPreference = $prevEa
}

Write-Host ""
Write-Host "Installed OK. Restart ComfyUI completely (close browser tab + stop python)." -ForegroundColor Green
Write-Host ""
Write-Host "UI entry: blue chat button on the RIGHT edge of the ComfyUI page." -ForegroundColor Cyan
Write-Host "  - Toggle: Enable Cursor Agent (edits workflows/ in repo)" -ForegroundColor DarkGray
Write-Host "  - Or use local Qwen via Ollama when Agent is OFF" -ForegroundColor DarkGray
Write-Host ""
Write-Host "Env (set by 启动ComfyUI.bat or one-click installer):" -ForegroundColor DarkGray
Write-Host "  JINFRAME_REPO_ROOT=$RepoRoot"
Write-Host "  COMFYUI_ROOT=$ComfyRoot"
