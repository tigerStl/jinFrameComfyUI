# Install missing deps for ComfyUI_LTX2_SM (opencv / cv2).
# Usage:
#   .\install\repair_ltx2_sm_deps.ps1
#   .\install\repair_ltx2_sm_deps.ps1 -ComfyRoot "K:\ComfyUI\ComfyUI"

param(
    [string]$ComfyRoot = $(if ($env:COMFYUI_ROOT) { $env:COMFYUI_ROOT } else { "C:\ComfyUI\ComfyUI" })
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path $PSScriptRoot -Parent
$ComfyRoot = [System.IO.Path]::GetFullPath($ComfyRoot)
$ltx = Join-Path $ComfyRoot "custom_nodes\ComfyUI_LTX2_SM"

if (-not (Test-Path (Join-Path $ltx "__init__.py"))) {
    throw "ComfyUI_LTX2_SM not found under $ComfyRoot\custom_nodes"
}

$Py = $env:JINFRAME_PYTHON
if (-not ($Py -and (Test-Path $Py))) {
    $cfg = Join-Path $RepoRoot "jinframe_install_paths.json"
    if (Test-Path $cfg) {
        $j = Get-Content $cfg -Raw | ConvertFrom-Json
        if ($j.python_home) {
            $Py = Join-Path $j.python_home "python.exe"
        }
    }
}
if (-not ($Py -and (Test-Path $Py))) {
    $drive = [System.IO.Path]::GetPathRoot($ComfyRoot)
    $Py = Join-Path $drive "tools\Python312\python.exe"
}
if (-not (Test-Path $Py)) {
    $Py = "python"
}

Write-Host "Python: $Py" -ForegroundColor Cyan
Write-Host "LTX2_SM: $ltx" -ForegroundColor Cyan

$req = Join-Path $ltx "requirements.txt"
if (Test-Path $req) {
    Write-Host "[pip] requirements.txt" -ForegroundColor Green
    & $Py -m pip install -r $req
}

Write-Host "[pip] opencv-python-headless (cv2)" -ForegroundColor Green
& $Py -m pip install opencv-python-headless

Write-Host "[verify] import cv2" -ForegroundColor Green
& $Py -c "import cv2; print('cv2 OK', cv2.__version__)"
Write-Host "Done. Restart ComfyUI." -ForegroundColor Green
