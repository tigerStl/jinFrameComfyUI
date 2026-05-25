# Repair ComfyUI Python env after one-click install (PYTHONPATH + pip requirements)
# Usage from repo root:
#   .\install\repair_comfyui_env.ps1
#   .\install\repair_comfyui_env.ps1 -ComfyRoot "K:\comfyui\ComfyUI"

param(
    [string]$ComfyRoot = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$PathsFile = Join-Path $RepoRoot "jinframe_install_paths.json"

if (-not $ComfyRoot -and (Test-Path $PathsFile)) {
    $cfg = Get-Content $PathsFile -Raw | ConvertFrom-Json
    if ($cfg.comfyui_root) { $ComfyRoot = $cfg.comfyui_root }
}
if (-not $ComfyRoot) {
    $ComfyRoot = $env:COMFYUI_ROOT
}
if (-not $ComfyRoot) {
    throw "Set -ComfyRoot or run one-click install first (jinframe_install_paths.json)."
}

$ComfyRoot = [System.IO.Path]::GetFullPath($ComfyRoot)
if (-not (Test-Path (Join-Path $ComfyRoot "comfy\options.py"))) {
    throw "Missing comfy package under $ComfyRoot — re-run: .\install\setup_comfyui.ps1 -ComfyRoot `"$ComfyRoot`""
}

$Py = $env:JINFRAME_PYTHON
if (-not $Py -or -not (Test-Path $Py)) {
    $driveRoot = [System.IO.Path]::GetPathRoot($ComfyRoot)
    $Py = Join-Path $driveRoot "tools\Python312\python.exe"
}
if (-not (Test-Path $Py)) { $Py = "python" }

Write-Host "ComfyRoot: $ComfyRoot" -ForegroundColor Cyan
Write-Host "Python:    $Py" -ForegroundColor Cyan
$env:PYTHONPATH = $ComfyRoot
$env:COMFYUI_ROOT = $ComfyRoot

& (Join-Path $PSScriptRoot "bootstrap_python_pip.ps1") -PythonExe $Py
$req = Join-Path $ComfyRoot "requirements.txt"
Write-Host "[pip] $req" -ForegroundColor Green
& $Py -m pip install -r $req

# Refresh launch bat via one-click installer or manual PYTHONPATH line
$bat = Join-Path $ComfyRoot "启动ComfyUI.bat"
Write-Host ""
Write-Host "Done. Start with: $bat" -ForegroundColor Green
Write-Host "Or: set PYTHONPATH=$ComfyRoot && `"$Py`" `"$(Join-Path $ComfyRoot 'main.py')`" --lowvram" -ForegroundColor Yellow
