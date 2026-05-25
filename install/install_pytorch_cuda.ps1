# Install PyTorch matching this machine's GPU (CUDA) or CPU fallback.
# Usage:
#   .\install\install_pytorch_cuda.ps1 -PythonExe "K:\tools\Python312\python.exe"
#   .\install\install_pytorch_cuda.ps1 -PythonExe "..." -RepoRoot "K:\tiger\jinFrame\jinFrameComfyUI"

param(
    [Parameter(Mandatory = $true)]
    [string]$PythonExe,
    [string]$RepoRoot = "",
    [ValidateSet("", "cpu", "cu124", "cu128_nightly")]
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

function Ensure-GpuProfile {
    if ($Profile) {
        return
    }
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
            }
            "cu124" {
                $p.torch_index_url = "https://download.pytorch.org/whl/cu124"
                $p.torch_nightly = $false
            }
            "cpu" {
                $p.torch_index_url = ""
                $p.torch_nightly = $false
            }
        }
    }
    return $p
}

function Test-TorchCudaOk {
    if (-not (Test-TorchInstalled)) {
        return $false
    }
    $probe = Join-Path $PSScriptRoot "probe_torch_cuda.py"
    if (-not (Test-Path $probe)) {
        throw "Missing probe_torch_cuda.py under install/"
    }
    $code = Invoke-Py -ScriptPath $probe
    return $code -eq 0
}

function Install-TorchFromIndex {
    param([string]$IndexUrl, [bool]$Nightly)
    Write-Log "pip uninstall torch / torchvision / torchaudio ..." "Yellow"
    Invoke-Pip -PipArgs @("uninstall", "-y", "torch", "torchvision", "torchaudio") | Out-Null

    $pipArgs = @("install", "--no-cache-dir", "--force-reinstall")
    if ($Nightly) { $pipArgs += "--pre" }
    $pipArgs += @("torch", "torchvision", "torchaudio", "--index-url", $IndexUrl)

    Write-Log "pip install torch from index (10-30 min possible) ..." "Cyan"
    $code = Invoke-Pip -PipArgs $pipArgs
    return ($code -eq 0)
}

Write-Log "=== JinFrame PyTorch setup ===" "Cyan"
Write-Log "Python: $PythonExe"

$gpu = Get-ProfileObject
Write-Log "GPU: $($gpu.gpu_name)" "Cyan"
Write-Log "Plan: $($gpu.torch_profile) | $($gpu.reason)" "DarkGray"

if ($gpu.torch_profile -eq "cpu") {
    Write-Log "CPU mode: keep PyTorch from requirements.txt (no CUDA wheels)." "Yellow"
    Write-Log "ComfyUI will use --cpu; install NVIDIA driver for GPU workflows." "Yellow"
    exit 0
}

if (Test-TorchCudaOk) {
    Write-Log "PyTorch CUDA already OK for this machine" "Green"
    Invoke-Py -ScriptPath (Join-Path $PSScriptRoot "probe_torch_cuda.py") | Out-Null
    exit 0
}

if (-not (Test-TorchInstalled)) {
    Write-Log "torch not installed yet; installing CUDA wheels ..." "DarkGray"
} else {
    Write-Log "torch present but CUDA not OK (likely CPU build); reinstalling CUDA wheels ..." "Yellow"
}
Write-Log "Installing PyTorch for profile: $($gpu.torch_profile)" "Yellow"

$ok = Install-TorchFromIndex -IndexUrl $gpu.torch_index_url -Nightly:([bool]$gpu.torch_nightly)
if ($ok -and (Test-TorchCudaOk)) {
    Write-Log "PyTorch CUDA install OK ($($gpu.torch_profile))" "Green"
    exit 0
}

if ($gpu.torch_profile -eq "cu128_nightly") {
    Write-Log "cu128 nightly failed verify; trying cu124 ..." "DarkYellow"
    if ((Install-TorchFromIndex -IndexUrl "https://download.pytorch.org/whl/cu124" -Nightly:$false) -and (Test-TorchCudaOk)) {
        $gpu.torch_profile = "cu124"
        $gpu.comfy_launch_extra = "--lowvram"
        $gpu | ConvertTo-Json -Depth 4 | Set-Content -Path $ProfileFile -Encoding UTF8
        Write-Log "Fallback cu124 OK; updated $ProfileFile" "Green"
        exit 0
    }
} else {
    Write-Log "cu124 failed verify; trying cu128 nightly ..." "DarkYellow"
    if ((Install-TorchFromIndex -IndexUrl "https://download.pytorch.org/whl/nightly/cu128" -Nightly:$true) -and (Test-TorchCudaOk)) {
        $gpu.torch_profile = "cu128_nightly"
        $gpu | ConvertTo-Json -Depth 4 | Set-Content -Path $ProfileFile -Encoding UTF8
        Write-Log "Fallback cu128 nightly OK" "Green"
        exit 0
    }
}

Write-Error @"
PyTorch CUDA install failed for $($gpu.gpu_name).
Profile tried: $($gpu.torch_profile)
Verify driver: nvidia-smi
Manual (RTX 3060 / 40 series):
  "$PythonExe" -m pip install --force-reinstall torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
Manual (RTX 5060 / 50 series):
  "$PythonExe" -m pip install --pre --force-reinstall torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128
"@
