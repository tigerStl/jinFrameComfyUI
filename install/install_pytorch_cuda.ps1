# Replace CPU-only PyTorch with CUDA build (required for ComfyUI on NVIDIA GPUs).
# RTX 50-series (5060/5070/5090, sm_120) needs cu128 nightly wheels.
# Usage:
#   .\install\install_pytorch_cuda.ps1 -PythonExe "K:\tools\Python312\python.exe"

param(
    [Parameter(Mandatory = $true)]
    [string]$PythonExe
)

$ErrorActionPreference = "Stop"
$PythonExe = [System.IO.Path]::GetFullPath($PythonExe)

function Write-Log([string]$Msg, [string]$Color = "White") {
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $Msg" -ForegroundColor $Color
}

function Invoke-Py {
    param([string[]]$PyArgs)
    $p = Start-Process -FilePath $PythonExe -ArgumentList $PyArgs -Wait -PassThru -NoNewWindow
    return $p.ExitCode
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
    param([string]$IndexUrl, [switch]$Nightly)
    Write-Log "pip uninstall torch / torchvision / torchaudio ..." "Yellow"
    & $PythonExe -m pip uninstall -y torch torchvision torchaudio 2>&1 | ForEach-Object { Write-Host "    $_" }

    $pipArgs = @("-m", "pip", "install", "--no-cache-dir")
    if ($Nightly) { $pipArgs += "--pre" }
    $pipArgs += @("torch", "torchvision", "torchaudio", "--index-url", $IndexUrl)

    Write-Log ("pip install " + ($pipArgs -join ' ')) "Cyan"
    & $PythonExe @pipArgs
    if ($LASTEXITCODE -ne 0) { return $false }
    return $true
}

Write-Log "=== JinFrame PyTorch CUDA setup ===" "Cyan"
Write-Log "Python: $PythonExe"

if (Test-TorchCudaOk) {
    Write-Log "PyTorch CUDA already OK" "Green"
    & $PythonExe -c "import torch; print('cuda', torch.version.cuda, torch.cuda.get_device_name(0))"
    exit 0
}

Write-Log "Current PyTorch has no CUDA (CPU build). Installing GPU wheels ..." "Yellow"
Write-Log "RTX 50-series needs cu128 nightly; older GPUs use cu124. This may take 10-30 min." "DarkGray"

# 1) RTX 5060 / 5070 / 5090 (sm_120) — cu128 nightly
if (Install-TorchFromIndex -IndexUrl "https://download.pytorch.org/whl/nightly/cu128" -Nightly) {
    if (Test-TorchCudaOk) {
        Write-Log "PyTorch cu128 nightly installed successfully" "Green"
        exit 0
    }
    Write-Log "cu128 nightly installed but CUDA test failed; trying cu124 ..." "DarkYellow"
}

# 2) RTX 30/40 etc. — stable cu124
if (Install-TorchFromIndex -IndexUrl "https://download.pytorch.org/whl/cu124") {
    if (Test-TorchCudaOk) {
        Write-Log "PyTorch cu124 installed successfully" "Green"
        exit 0
    }
}

Write-Error @"
PyTorch CUDA install failed.
Manual fix (RTX 5060 / 50-series):
  "$PythonExe" -m pip uninstall -y torch torchvision torchaudio
  "$PythonExe" -m pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128 --no-cache-dir
Verify:
  "$PythonExe" -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
"@
