# Install pinned ComfyUI + custom nodes from COMFYUI.lock.json
# Usage (from repo root):
#   .\install\setup_comfyui.ps1
#   .\install\setup_comfyui.ps1 -ComfyRoot "K:\ComfyUI\ComfyUI"
#   .\install\setup_comfyui.ps1 -ComfyRoot "K:\ComfyUI\ComfyUI" -Force   # re-fetch git + pip

param(
    [string]$ComfyRoot = "",
    [switch]$SkipPip,
    [switch]$Force
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
if (-not $Force) {
    Write-Host "Fast mode: skip git/pip when already at locked revision (use -Force to redo)." -ForegroundColor DarkGray
}
Write-Host ""

function Get-GitHead {
    param([string]$Path)
    if (-not (Test-Path (Join-Path $Path ".git"))) { return $null }
    $h = (git -C $Path rev-parse HEAD 2>$null | Out-String).Trim()
    if ($h.Length -lt 12) { return $null }
    return $h
}

function Test-AtRevision {
    param([string]$Path, [string]$Revision)
    $head = Get-GitHead -Path $Path
    if (-not $head) { return $false }
    return ($head -eq $Revision) -or $head.StartsWith($Revision.Substring(0, 12))
}

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
        if ((-not $Force) -and (Test-AtRevision -Path $Path -Revision $Revision)) {
            Write-Host "[git] skip $Label (already $($Revision.Substring(0,12)))" -ForegroundColor DarkGray
            return
        }
        Write-Host "[git] sync $Label -> $($Revision.Substring(0,12))..." -ForegroundColor Yellow
        # Shallow fetch of target commit only (faster than full fetch origin)
        git -C $Path fetch --depth 1 origin $Revision 2>$null
        if ($LASTEXITCODE -ne 0) {
            git -C $Path fetch origin 2>$null
        }
        git -C $Path checkout -f $Revision
        return
    }

    if ((Test-Path $Path) -and ((Get-ChildItem $Path -Force | Measure-Object).Count -gt 0)) {
        if ((-not $Force) -and (Test-Path (Join-Path $Path "main.py")) -and (Test-Path (Join-Path $Path "comfy\options.py"))) {
            Write-Host "[git] skip clone $Label (existing ComfyUI tree, no .git)" -ForegroundColor DarkYellow
            return
        }
        Remove-Item $Path -Recurse -Force
    }

    Write-Host "[git] clone $Label" -ForegroundColor Green
    if ($Tag) {
        git clone --depth 1 --branch $Tag $Url $Path
        if ($LASTEXITCODE -ne 0) { throw "git clone failed: $Label" }
    } else {
        # Full clone required for arbitrary pinned commits (shallow clone breaks checkout on some repos)
        git clone $Url $Path
        if ($LASTEXITCODE -ne 0) { throw "git clone failed: $Label" }
        git -C $Path checkout -f $Revision
        if ($LASTEXITCODE -ne 0) {
            Remove-Item $Path -Recurse -Force -ErrorAction SilentlyContinue
            throw "git checkout $Revision failed for $Label (removed broken folder). Re-run setup."
        }
    }
    if (-not (Test-AtRevision -Path $Path -Revision $Revision)) {
        throw "git verify failed: $Label is not at $($Revision.Substring(0,12))"
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

function Test-ComfyCanImport {
    param([string]$Py, [string]$ComfyRoot)
    if (-not (Test-Path (Join-Path $ComfyRoot "comfy\options.py"))) { return $false }
    $env:PYTHONPATH = $ComfyRoot
    $root = ($ComfyRoot -replace '\\', '/')
    $probe = Join-Path $env:TEMP "jinframe_probe_comfy.py"
    @"
import sys
sys.path.insert(0, r'$root')
import comfy
"@ | Set-Content -Path $probe -Encoding UTF8
    $p = Start-Process -FilePath $Py -ArgumentList @($probe) -Wait -PassThru -NoNewWindow
    Remove-Item $probe -Force -ErrorAction SilentlyContinue
    return $p.ExitCode -eq 0
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

    $bootstrap = Join-Path $PSScriptRoot "bootstrap_python_pip.ps1"
    & $bootstrap -PythonExe $Py

    if ((-not $Force) -and (Test-ComfyCanImport -Py $Py -ComfyRoot $ComfyRoot)) {
        Write-Host "[pip] skip ComfyUI requirements.txt (comfy import OK; use -Force to reinstall)" -ForegroundColor DarkGray
    } else {
        $reqMain = Join-Path $ComfyRoot "requirements.txt"
        if (Test-Path $reqMain) {
            Write-Host "[pip] ComfyUI requirements.txt (first install may take 10-30+ min)..." -ForegroundColor Green
            & $Py -m pip install -r $reqMain --upgrade-strategy only-if-needed
            if ($LASTEXITCODE -ne 0) {
                throw "pip install ComfyUI requirements failed. Try: `"$Py`" -m pip install -r `"$reqMain`""
            }
        }
    }

    foreach ($node in $Lock.custom_nodes) {
        $req = $node.pip_requirements
        if (-not $req) { continue }
        $reqPath = Join-Path $CustomNodes (Join-Path $node.name $req)
        if (-not (Test-Path $reqPath)) { continue }
        if ($Force) {
            Write-Host "[pip] $($node.name) (-Force)" -ForegroundColor Green
            & $Py -m pip install -r $reqPath --upgrade-strategy only-if-needed
            continue
        }
        Write-Host "[pip] $($node.name) (only-if-needed)..." -ForegroundColor DarkGray
        & $Py -m pip install -r $reqPath --upgrade-strategy only-if-needed -q
    }
}

$env:COMFYUI_ROOT = $ComfyRoot
Write-Host ""
Write-Host "ComfyUI setup done." -ForegroundColor Green
Write-Host "Next: install_jinframe_assistant.ps1, sync_to_comfyui.ps1, MODELS.md" -ForegroundColor Cyan
Write-Host "Start: cd `"$ComfyRoot`" ; .\启动ComfyUI.bat" -ForegroundColor Cyan
