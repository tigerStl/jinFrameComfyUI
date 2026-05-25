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
    param([string[]]$PyArgs)
    $p = Start-Process -FilePath $PythonExe -ArgumentList $PyArgs -Wait -PassThru -NoNewWindow
    return $p.ExitCode
}

function Ensure-GpuProfile {
    if ($Profile) {
        return
    }
    if (-not (Test-Path $ProfileFile)) {
        & (Join-Path $PSScriptRoot "detect_nvidia_gpu.ps1") -RepoRoot $RepoRoot -OutFile $ProfileFile
    }
    if (-not (Test-Path $ProfileFile)) {
        throw "Missing $ProfileFile — run detect_nvidia_gpu.ps1 first"
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
    $probe = Join-Path $env:TEMP "jinframe_probe_torch_cuda.py"
    @"
import torch
if not torch.cuda.is_available():
    raise SystemExit(1)
if not getattr(torch.version, "cuda", None):
    raise SystemExit(2)
print("torch", torch.__version__, "cuda", torch.version.cuda)
print("device", torch.cuda.get_device_name(0))
"@ | Set-Content -Path $probe -Encoding UTF8
    $code = Invoke-Py -PyArgs @($probe)
    Remove-Item $probe -Force -ErrorAction SilentlyContinue
    return $code -eq 0
}

function Install-TorchFromIndex {
    param([string]$IndexUrl, [bool]$Nightly)
    Write-Log "pip uninstall torch / torchvision / torchaudio ..." "Yellow"
    & $PythonExe -m pip uninstall -y torch torchvision torchaudio 2>&1 | ForEach-Object { Write-Host "    $_" }

    $pipArgs = @("-m", "pip", "install", "--no-cache-dir")
    if ($Nightly) { $pipArgs += "--pre" }
    $pipArgs += @("torch", "torchvision", "torchaudio", "--index-url", $IndexUrl)

    Write-Log ("pip install torch from index (10-30 min possible) ...") "Cyan"
    & $PythonExe @pipArgs
    return ($LASTEXITCODE -eq 0)
}

Write-Log "=== JinFrame PyTorch setup ===" "Cyan"
Write-Log "Python: $PythonExe"

$gpu = Get-ProfileObject
Write-Log "GPU: $($gpu.gpu_name)" "Cyan"
Write-Log "Plan: $($gpu.torch_profile) — $($gpu.reason)" "DarkGray"

if ($gpu.torch_profile -eq "cpu") {
    Write-Log "CPU mode: keep PyTorch from requirements.txt (no CUDA wheels)." "Yellow"
    Write-Log "ComfyUI will use --cpu; GPU workflows will not work until NVIDIA driver is installed." "Yellow"
    exit 0
}

if (Test-TorchCudaOk) {
    Write-Log "PyTorch CUDA already OK for this machine" "Green"
    & $PythonExe -c "import torch; print(torch.cuda.get_device_name(0))"
    exit 0
}

Write-Log "Installing PyTorch for profile: $($gpu.torch_profile)" "Yellow"

$ok = Install-TorchFromIndex -IndexUrl $gpu.torch_index_url -Nightly:([bool]$gpu.torch_nightly)
if ($ok -and (Test-TorchCudaOk)) {
    Write-Log "PyTorch CUDA install OK ($($gpu.torch_profile))" "Green"
    exit 0
}

# Fallback: opposite mainstream index (50xx nightly <-> cu124)
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
Manual (RTX 3060 / 40系):
  "$PythonExe" -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
Manual (RTX 5060 / 50系):
  "$PythonExe" -m pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128
"@
