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
$script:PhaseStart = Get-Date
$script:StepIndex = 0
$script:StepTotal = 7

function Write-Log {
    param([string]$Message, [string]$Color = "White")
    $ts = Get-Date -Format "HH:mm:ss"
    Write-Host "[$ts] $Message" -ForegroundColor $Color
}

function Write-Phase {
    param([string]$Title)
    $script:StepIndex++
    $elapsed = (Get-Date) - $script:PhaseStart
    $elStr = "{0:mm\:ss}" -f $elapsed
    Write-Host ""
    Write-Log "==== [$script:StepIndex/$script:StepTotal] $Title | elapsed $elStr ====" "Cyan"
}

function Invoke-Git {
    param([string[]]$GitArgs)
    $argStr = $GitArgs -join ' '
    Write-Log "git $argStr" "DarkGray"
    & git @GitArgs
    if ($LASTEXITCODE -ne 0) {
        throw "git failed ($LASTEXITCODE): git $argStr"
    }
}

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

Write-Log "=== JinFrame ComfyUI setup (pinned) ===" "Cyan"
Write-Log "Repo:  $RepoRoot"
Write-Log "Comfy: $ComfyRoot"
Write-Log "Lock:  ComfyUI $($Lock.comfyui.tag) @ $($Lock.comfyui.revision.Substring(0,12))..."
if (-not $Force) {
    Write-Log "Fast mode: skip git/pip when already at locked revision (-Force to redo)." "DarkGray"
} else {
    Write-Log "Force mode: will re-sync git and pip." "Yellow"
}
Write-Log "Typical time: git 2-10 min; first pip 15-45 min; already installed ~1-3 min." "DarkGray"

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
            Write-Log "[git] skip $Label (already $($Revision.Substring(0,12)))" "DarkGray"
            return
        }
        Write-Log "[git] sync $Label -> $($Revision.Substring(0,12)) ..." "Yellow"
        & git -C $Path fetch --progress --depth 1 origin $Revision 2>&1 | ForEach-Object { Write-Host "    $_" }
        if ($LASTEXITCODE -ne 0) {
            Write-Log "[git] shallow fetch failed, trying full fetch ..." "DarkYellow"
            & git -C $Path fetch --progress origin 2>&1 | ForEach-Object { Write-Host "    $_" }
            if ($LASTEXITCODE -ne 0) { throw "git fetch failed for $Label" }
        }
        Invoke-Git -GitArgs @("-C", $Path, "checkout", "-f", $Revision)
        return
    }

    if ((Test-Path $Path) -and ((Get-ChildItem $Path -Force | Measure-Object).Count -gt 0)) {
        if ((-not $Force) -and (Test-Path (Join-Path $Path "main.py")) -and (Test-Path (Join-Path $Path "comfy\options.py"))) {
            Write-Log "[git] skip clone $Label (existing tree, no .git)" "DarkYellow"
            return
        }
        Write-Log "[git] remove incomplete folder $Path" "Yellow"
        Remove-Item $Path -Recurse -Force
    }

    Write-Log "[git] clone $Label - network speed varies ..." "Green"
    if ($Tag) {
        Invoke-Git -GitArgs @("clone", "--progress", "--depth", "1", "--branch", $Tag, $Url, $Path)
    } else {
        Invoke-Git -GitArgs @("clone", "--progress", $Url, $Path)
        Invoke-Git -GitArgs @("-C", $Path, "checkout", "-f", $Revision)
    }
    if (-not (Test-AtRevision -Path $Path -Revision $Revision)) {
        throw "git verify failed: $Label is not at $($Revision.Substring(0,12))"
    }
    $h = Get-GitHead -Path $Path
    Write-Log "[git] OK $Label @ $($h.Substring(0, [Math]::Min(12, $h.Length)))" "Green"
}

Write-Phase "ComfyUI core (git)"
$tag = $Lock.comfyui.tag
$rev = $Lock.comfyui.revision
Ensure-GitRepo -Url $Lock.comfyui.repo -Path $ComfyRoot -Revision $rev -Tag $tag -Label "ComfyUI $tag"

Write-Phase "Custom nodes (git)"
$nodeNum = 0
$requiredNodes = @($Lock.custom_nodes | Where-Object { $_.required })
foreach ($node in $requiredNodes) {
    $nodeNum++
    Write-Log "Node $nodeNum/$($requiredNodes.Count): $($node.name)" "Cyan"
    $dest = Join-Path $CustomNodes $node.name
    Ensure-GitRepo -Url $node.repo -Path $dest -Revision $node.revision -Label $node.name -Tag ""
}

Write-Phase "Model folders"
$models = Join-Path $ComfyRoot "models"
foreach ($sub in $Lock.model_subdirs) {
    New-Item -ItemType Directory -Force -Path (Join-Path $models $sub) | Out-Null
}
Write-Log "models\ subdirs ready" "DarkGray"

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
    Write-Log "probe import comfy ..." "DarkGray"
    $p = Start-Process -FilePath $Py -ArgumentList @($probe) -Wait -PassThru -NoNewWindow
    Remove-Item $probe -Force -ErrorAction SilentlyContinue
    return $p.ExitCode -eq 0
}

Write-Phase "Verify ComfyUI source"
$comfyPkg = Join-Path $ComfyRoot "comfy"
if (-not (Test-Path (Join-Path $comfyPkg "options.py"))) {
    throw @"
ComfyUI 源码不完整：未找到 $comfyPkg\options.py
请确认 Git 已安装且网络可访问 GitHub，然后重新运行：
  .\install\setup_comfyui.ps1 -ComfyRoot "$ComfyRoot"
若目录曾有残缺文件，可先删除整个 $ComfyRoot 后重试。
"@
}
Write-Log "comfy\options.py OK" "Green"

if (-not $SkipPip) {
    Write-Phase "Python dependencies (pip)"
    $Py = Resolve-PythonForComfy -ComfyRoot $ComfyRoot
    Write-Log "Python: $Py" "Cyan"
    $env:PYTHONPATH = $ComfyRoot
    $env:PIP_PROGRESS_BAR = "on"

    $bootstrap = Join-Path $PSScriptRoot "bootstrap_python_pip.ps1"
    Write-Log "bootstrap pip ..." "DarkGray"
    & $bootstrap -PythonExe $Py

    if ((-not $Force) -and (Test-ComfyCanImport -Py $Py -ComfyRoot $ComfyRoot)) {
        Write-Log "skip ComfyUI requirements.txt - comfy import OK" "DarkGray"
    } else {
        $reqMain = Join-Path $ComfyRoot "requirements.txt"
        if (Test-Path $reqMain) {
            Write-Log "pip install ComfyUI requirements.txt - FIRST RUN often 15-45 min, please wait" "Yellow"
            Write-Log 'You should see download lines below: Collecting / Downloading' "DarkGray"
            & $Py -m pip install -r $reqMain --upgrade-strategy only-if-needed --progress-bar on
            if ($LASTEXITCODE -ne 0) {
                throw "pip install ComfyUI requirements failed. Try: `"$Py`" -m pip install -r `"$reqMain`""
            }
            Write-Log "ComfyUI requirements.txt done" "Green"
        }
    }

    Write-Phase "PyTorch CUDA (GPU)"
    & (Join-Path $PSScriptRoot "install_pytorch_cuda.ps1") -PythonExe $Py
    if ($LASTEXITCODE -ne 0) {
        throw "PyTorch CUDA setup failed. ComfyUI needs NVIDIA GPU build of torch, not CPU-only."
    }

    $pipNodes = @($Lock.custom_nodes | Where-Object { $_.pip_requirements })
    $n = 0
    foreach ($node in $pipNodes) {
        $n++
        $reqPath = Join-Path $CustomNodes (Join-Path $node.name $node.pip_requirements)
        if (-not (Test-Path $reqPath)) { continue }
        Write-Log "pip [$n/$($pipNodes.Count)] $($node.name) ..." "Green"
        if ($Force) {
            & $Py -m pip install -r $reqPath --upgrade-strategy only-if-needed --progress-bar on
        } else {
            & $Py -m pip install -r $reqPath --upgrade-strategy only-if-needed --progress-bar on
        }
    }
} else {
    Write-Phase "Skip pip (-SkipPip)"
}

$env:COMFYUI_ROOT = $ComfyRoot
$total = (Get-Date) - $script:PhaseStart
Write-Host ""
Write-Log ("ComfyUI setup done. Total {0:mm\:ss}" -f $total) "Green"
Write-Log "Next: install_jinframe_assistant.ps1, sync_to_comfyui.ps1, MODELS.md" "Cyan"
$launchBat = Join-Path $ComfyRoot "启动ComfyUI.bat"
Write-Log "Start: $launchBat" "Cyan"
