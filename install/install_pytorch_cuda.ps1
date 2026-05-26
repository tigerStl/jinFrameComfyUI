# Install PyTorch matching this machine's GPU (CUDA) or CPU fallback.
# Profiles: cu130 (RTX 3050/30/40), cu128_nightly (RTX 5060/50), cpu
# Usage:
#   .\install\install_pytorch_cuda.ps1 -PythonExe "K:\tools\Python312\python.exe" -RepoRoot "..."

param(
    [Parameter(Mandatory = $true)]
    [string]$PythonExe,
    [string]$RepoRoot = "",
    [ValidateSet("", "cpu", "cu130", "cu124", "cu128_nightly")]
    [string]$Profile = ""
)

$ErrorActionPreference = "Stop"
$PythonExe = [System.IO.Path]::GetFullPath($PythonExe)

if (-not $RepoRoot) {
    $RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
}
$RepoRoot = [System.IO.Path]::GetFullPath($RepoRoot)
$ProfileFile = Join-Path $RepoRoot "jinframe_gpu_profile.json"

function Write-Log([string]$Msg, [string]$Color = "White") {
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $Msg" -ForegroundColor $Color
}

function Invoke-Py {
    param([string]$ScriptPath)
    $p = Start-Process -FilePath $PythonExe -ArgumentList @($ScriptPath) -Wait -PassThru -NoNewWindow
    return $p.ExitCode
}

function Invoke-Pip {
    param([string[]]$PipArgs)
    $allArgs = @("-m", "pip") + $PipArgs
    $prevEa = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $p = Start-Process -FilePath $PythonExe -ArgumentList $allArgs -Wait -PassThru -NoNewWindow
        return $p.ExitCode
    } finally {
        $ErrorActionPreference = $prevEa
    }
}

function Test-TorchInstalled {
    $probe = Join-Path $PSScriptRoot "probe_import_torch.py"
    if (-not (Test-Path $probe)) {
        throw "Missing probe_import_torch.py under install/"
    }
    return (Invoke-Py -ScriptPath $probe) -eq 0
}

function Set-ProbeEnv($gpu) {
    $env:JINFRAME_REPO_ROOT = $RepoRoot
    if ($gpu.min_cuda_major) {
        $env:JINFRAME_MIN_CUDA_MAJOR = [string]$gpu.min_cuda_major
    } elseif ($gpu.torch_profile -eq "cu128_nightly") {
        $env:JINFRAME_MIN_CUDA_MAJOR = "12"
    } else {
        $env:JINFRAME_MIN_CUDA_MAJOR = "13"
    }
}

function Ensure-GpuProfile {
    if ($Profile) { return }
    if (-not (Test-Path $ProfileFile)) {
        & (Join-Path $PSScriptRoot "detect_nvidia_gpu.ps1") -RepoRoot $RepoRoot -OutFile $ProfileFile
    }
    if (-not (Test-Path $ProfileFile)) {
        throw "Missing $ProfileFile - run detect_nvidia_gpu.ps1 first"
    }
}

function Get-ProfileObject {
    Ensure-GpuProfile
    $p = Get-Content $ProfileFile -Raw | ConvertFrom-Json
    if ($Profile) {
        $p | Add-Member -NotePropertyName torch_profile -NotePropertyValue $Profile -Force
        switch ($Profile) {
            "cu128_nightly" {
                $p.torch_index_url = "https://download.pytorch.org/whl/nightly/cu128"
                $p.torch_nightly = $true
                $p.min_cuda_major = 12
            }
            "cu130" {
                $p.torch_index_url = "https://download.pytorch.org/whl/cu130"
                $p.torch_nightly = $false
                $p.min_cuda_major = 13
            }
            "cu124" {
                $p.torch_index_url = "https://download.pytorch.org/whl/cu124"
                $p.torch_nightly = $false
                $p.min_cuda_major = 13
                Write-Log "cu124 is outdated; upgrading to cu130 for ComfyUI 0.21+" "Yellow"
                $p.torch_profile = "cu130"
                $p.torch_index_url = "https://download.pytorch.org/whl/cu130"
            }
            "cpu" {
                $p.torch_index_url = ""
                $p.torch_nightly = $false
            }
        }
    }
    if ($p.torch_profile -eq "cu124") {
        Write-Log "Profile cu124 -> cu130 (ComfyUI 0.21+)" "Yellow"
        $p.torch_profile = "cu130"
        $p.torch_index_url = "https://download.pytorch.org/whl/cu130"
        $p.torch_nightly = $false
        $p.min_cuda_major = 13
    }
    if ($null -eq $p.min_cuda_major) {
        if ($p.torch_profile -eq "cu128_nightly") {
            $p | Add-Member -NotePropertyName min_cuda_major -NotePropertyValue 12 -Force
        } else {
            $p | Add-Member -NotePropertyName min_cuda_major -NotePropertyValue 13 -Force
        }
    }
    if (-not $p.comfy_launch_extra -or $p.comfy_launch_extra -eq "--lowvram") {
        $p.comfy_launch_extra = "--lowvram --disable-cuda-malloc"
    }
    return $p
}

function Test-TorchCudaOk($gpu) {
    if (-not (Test-TorchInstalled)) { return $false }
    Set-ProbeEnv $gpu
    $probe = Join-Path $PSScriptRoot "probe_torch_cuda.py"
    $code = Invoke-Py -ScriptPath $probe
    if ($code -eq 4) {
        Write-Log "PyTorch CUDA build too old for profile $($gpu.torch_profile)" "Yellow"
    } elseif ($code -eq 5) {
        Write-Log "CUDA init failed; try --disable-cuda-malloc in launch bat" "Yellow"
    }
    return $code -eq 0
}

function Install-TorchFromIndex {
    param([string]$IndexUrl, [bool]$Nightly, [switch]$UseExtraIndex)
    Write-Log "pip uninstall torch / torchvision / torchaudio ..." "Yellow"
    Invoke-Pip -PipArgs @("uninstall", "-y", "torch", "torchvision", "torchaudio") | Out-Null

    $pipArgs = @("install", "--no-cache-dir", "--force-reinstall")
    if ($Nightly) { $pipArgs += "--pre" }
    if ($UseExtraIndex) {
        $pipArgs += @("torch", "torchvision", "torchaudio", "--extra-index-url", $IndexUrl)
    } else {
        $pipArgs += @("torch", "torchvision", "torchaudio", "--index-url", $IndexUrl)
    }

    Write-Log "pip install from $IndexUrl (10-30 min) ..." "Cyan"
    return (Invoke-Pip -PipArgs $pipArgs) -eq 0
}

function Save-GpuProfile($gpu) {
    $gpu | ConvertTo-Json -Depth 4 | Set-Content -Path $ProfileFile -Encoding UTF8
}

Write-Log "=== JinFrame PyTorch setup ===" "Cyan"
Write-Log "Python: $PythonExe"

$gpu = Get-ProfileObject
Set-ProbeEnv $gpu
Write-Log "GPU: $($gpu.gpu_name)" "Cyan"
Write-Log "Plan: $($gpu.torch_profile) | $($gpu.reason)" "DarkGray"
Write-Log "Launch: $($gpu.comfy_launch_extra)" "DarkGray"

if ($gpu.torch_profile -eq "cpu") {
    Write-Log "CPU mode: no CUDA wheels." "Yellow"
    exit 0
}

if (Test-TorchCudaOk $gpu) {
    Write-Log "PyTorch CUDA OK for $($gpu.torch_profile)" "Green"
    Save-GpuProfile $gpu
    Invoke-Py -ScriptPath (Join-Path $PSScriptRoot "probe_torch_cuda.py") | Out-Null
    exit 0
}

Write-Log "Installing PyTorch: $($gpu.torch_profile)" "Yellow"

$ok = Install-TorchFromIndex -IndexUrl $gpu.torch_index_url -Nightly:([bool]$gpu.torch_nightly)
if (-not $ok -and $gpu.torch_profile -eq "cu130") {
    Write-Log "Retry cu130 with extra-index-url ..." "DarkYellow"
    $ok = Install-TorchFromIndex -IndexUrl $gpu.torch_index_url -Nightly:$false -UseExtraIndex
}
if ($ok -and (Test-TorchCudaOk $gpu)) {
    Write-Log "PyTorch install OK ($($gpu.torch_profile))" "Green"
    Save-GpuProfile $gpu
    exit 0
}

if ($gpu.torch_profile -eq "cu128_nightly") {
    Write-Log "cu128 nightly failed; trying cu130 (may not support 5060 sm_120) ..." "DarkYellow"
    $gpu.torch_profile = "cu130"
    $gpu.torch_index_url = "https://download.pytorch.org/whl/cu130"
    $gpu.torch_nightly = $false
    $gpu.min_cuda_major = 13
    if ((Install-TorchFromIndex -IndexUrl $gpu.torch_index_url -Nightly:$false) -and (Test-TorchCudaOk $gpu)) {
        Save-GpuProfile $gpu
        Write-Log "Fallback cu130 OK" "Green"
        exit 0
    }
} else {
    Write-Log "cu130 failed; trying cu128 nightly (RTX 50 / 5060) ..." "DarkYellow"
    $gpu.torch_profile = "cu128_nightly"
    $gpu.torch_index_url = "https://download.pytorch.org/whl/nightly/cu128"
    $gpu.torch_nightly = $true
    $gpu.min_cuda_major = 12
    if ((Install-TorchFromIndex -IndexUrl $gpu.torch_index_url -Nightly:$true) -and (Test-TorchCudaOk $gpu)) {
        Save-GpuProfile $gpu
        Write-Log "Fallback cu128 nightly OK" "Green"
        exit 0
    }
}

Write-Error @"
PyTorch CUDA install failed for $($gpu.gpu_name).
RTX 3050 / 30-40: cu130 + --lowvram --disable-cuda-malloc
RTX 5060 / 50:    cu128 nightly + same launch flags

  powershell -File "$PSScriptRoot\repair_comfyui_cuda.ps1" -ComfyRoot "YOUR_COMFY_ROOT"
"@
