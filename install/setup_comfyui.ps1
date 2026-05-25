# Install pinned ComfyUI + custom nodes from COMFYUI.lock.json
# Usage (from repo root):
#   .\install\setup_comfyui.ps1
#   .\install\setup_comfyui.ps1 -ComfyRoot "D:\ComfyUI\ComfyUI"
#
# Default install folder when -ComfyRoot omitted: .\comfyui\ComfyUI (under this repo, gitignored)

param(
    [string]$ComfyRoot = "",
    [switch]$SkipPip
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$LockFile = Join-Path $RepoRoot "COMFYUI.lock.json"

if (-not (Test-Path $LockFile)) {
    throw "Missing COMFYUI.lock.json"
}

$Lock = Get-Content $LockFile -Raw | ConvertFrom-Json

if (-not $ComfyRoot) {
    $ComfyRoot = Join-Path $RepoRoot "comfyui\ComfyUI"
}
$ComfyRoot = [System.IO.Path]::GetFullPath($ComfyRoot)
$CustomNodes = Join-Path $ComfyRoot "custom_nodes"

Write-Host "=== JinFrame ComfyUI setup (pinned) ===" -ForegroundColor Cyan
Write-Host "Repo:  $RepoRoot"
Write-Host "Comfy: $ComfyRoot"
Write-Host "Lock:  ComfyUI $($Lock.comfyui.tag) @ $($Lock.comfyui.revision.Substring(0,12))..."
Write-Host ""

function Ensure-GitRepo {
    param(
        [string]$Url,
        [string]$Path,
        [string]$Revision,
        [string]$Label = "",
        [string]$Tag = ""
    )
    $parent = Split-Path $Path -Parent
    if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }

    if (Test-Path (Join-Path $Path ".git")) {
        Write-Host "[git] sync $Label -> $($Revision.Substring(0,12))..." -ForegroundColor Yellow
        git -C $Path fetch origin 2>$null
        git -C $Path checkout -f $Revision
        return
    }
    if (Test-Path $Path) { Remove-Item $Path -Recurse -Force }
    Write-Host "[git] clone $Label" -ForegroundColor Green
    if ($Tag) {
        git clone --depth 1 --branch $Tag $Url $Path
    } else {
        git clone $Url $Path
        git -C $Path checkout -f $Revision
    }
}

# --- ComfyUI core ---
$tag = $Lock.comfyui.tag
$rev = $Lock.comfyui.revision
Ensure-GitRepo -Url $Lock.comfyui.repo -Path $ComfyRoot -Revision $rev -Tag $tag -Label "ComfyUI $tag"

# --- custom nodes ---
foreach ($node in $Lock.custom_nodes) {
    if (-not $node.required) { continue }
    $dest = Join-Path $CustomNodes $node.name
    Ensure-GitRepo -Url $node.repo -Path $dest -Revision $node.revision -Label $node.name -Tag ""
}

# --- model dirs ---
$models = Join-Path $ComfyRoot "models"
foreach ($sub in $Lock.model_subdirs) {
    New-Item -ItemType Directory -Force -Path (Join-Path $models $sub) | Out-Null
}

function Resolve-PythonForComfy {
    param([string]$ComfyRoot)
    if ($env:JINFRAME_PYTHON -and (Test-Path $env:JINFRAME_PYTHON)) {
        return $env:JINFRAME_PYTHON
    }
    $driveRoot = [System.IO.Path]::GetPathRoot($ComfyRoot)
    if ($driveRoot) {
        $toolsPy = Join-Path $driveRoot "tools\Python312\python.exe"
        if (Test-Path $toolsPy) { return $toolsPy }
    }
    $emb = Join-Path (Split-Path $ComfyRoot -Parent) "python_embeded\python.exe"
    if (Test-Path $emb) { return $emb }
    return "python"
}

# --- verify clone ---
$comfyPkg = Join-Path $ComfyRoot "comfy"
if (-not (Test-Path (Join-Path $comfyPkg "options.py"))) {
    throw @"
ComfyUI 源码不完整：未找到 $comfyPkg\options.py
请确认 Git 已安装且网络可访问 GitHub，然后重新运行：
  .\install\setup_comfyui.ps1 -ComfyRoot "$ComfyRoot"
若目录曾有残缺文件，可先删除整个 $ComfyRoot 后重试。
"@
}

# --- pip ---
if (-not $SkipPip) {
    $Py = Resolve-PythonForComfy -ComfyRoot $ComfyRoot
    Write-Host "[python] $Py" -ForegroundColor Cyan
    $env:PYTHONPATH = $ComfyRoot

    & $Py -m pip --version 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[pip] bootstrap (ensurepip)..." -ForegroundColor Yellow
        & $Py -m ensurepip --upgrade
    }

    $reqMain = Join-Path $ComfyRoot "requirements.txt"
    if (Test-Path $reqMain) {
        Write-Host "[pip] ComfyUI requirements.txt (may take several minutes)..." -ForegroundColor Green
        & $Py -m pip install -r $reqMain
        if ($LASTEXITCODE -ne 0) {
            throw "pip install ComfyUI requirements failed. Try: `"$Py`" -m pip install -r `"$reqMain`""
        }
    }

    foreach ($node in $Lock.custom_nodes) {
        $req = $node.pip_requirements
        if (-not $req) { continue }
        $reqPath = Join-Path $CustomNodes (Join-Path $node.name $req)
        if (Test-Path $reqPath) {
            Write-Host "[pip] $($node.name)" -ForegroundColor Green
            & $Py -m pip install -r $reqPath
        }
    }
}

$env:COMFYUI_ROOT = $ComfyRoot
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  .\install\install_jinframe_assistant.ps1 -ComfyRoot `"$ComfyRoot`""
Write-Host "  .\install\sync_to_comfyui.ps1 -ComfyRoot `"$ComfyRoot`""
Write-Host "  See MODELS.md for model downloads"
Write-Host ""
Write-Host "Start ComfyUI (8GB GPU example):" -ForegroundColor Cyan
Write-Host "  cd `"$ComfyRoot`""
Write-Host "  python main.py $($Lock.launch.low_vram_args)"
