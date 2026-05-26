# Install PyTorch for this GPU: cu130 (3050/30/40) or cu128 nightly (5060/50)
# Usage:
#   .\install\install_pytorch_cuda.ps1 -PythonExe "K:\tools\Python312\python.exe" -RepoRoot "..."

param(
    [Parameter(Mandatory = $true)]
    [string]$PythonExe,
    [string]$RepoRoot = "",
    [ValidateSet("", "cpu", "cu130", "cu128_nightly")]
    [string]$Profile = "",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "gpu_common.ps1")

$PythonExe = [System.IO.Path]::GetFullPath($PythonExe)
if (-not $RepoRoot) {
    $RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
}
$RepoRoot = [System.IO.Path]::GetFullPath($RepoRoot)
$ProfileFile = Join-Path $RepoRoot "jinframe_gpu_profile.json"

function Write-Log([string]$Msg, [string]$Color = "White") {
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $Msg" -ForegroundColor $Color
}

function Invoke-Py([string]$ScriptPath) {
    return (Start-Process -FilePath $PythonExe -ArgumentList @($ScriptPath) -Wait -PassThru -NoNewWindow).ExitCode
}

function Invoke-Pip([string[]]$PipArgs) {
    $allArgs = @("-m", "pip") + $PipArgs
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        return (Start-Process -FilePath $PythonExe -ArgumentList $allArgs -Wait -PassThru -NoNewWindow).ExitCode
    } finally {
        $ErrorActionPreference = $prev
    }
}

function Set-ProbeEnv($gpu) {
    $env:JINFRAME_REPO_ROOT = $RepoRoot
    if ($null -ne $gpu.min_cuda_major -and "$($gpu.min_cuda_major)" -ne "") {
        $env:JINFRAME_MIN_CUDA_MAJOR = [string]$gpu.min_cuda_major
    } else {
        $env:JINFRAME_MIN_CUDA_MAJOR = "13"
    }
}

function Invoke-DetectGpu {
    & (Join-Path $PSScriptRoot "detect_nvidia_gpu.ps1") -RepoRoot $RepoRoot -OutFile $ProfileFile
    if ($LASTEXITCODE -eq 2) {
        throw "nvidia-smi reports GPU IS LOST. Reboot the PC first."
    }
}

function Get-GpuProfile {
    $smi = Get-SmiGpuInfo
    if ($smi.lost) { throw "GPU IS LOST. Reboot before installing PyTorch." }

    $mustDetect = $Force.IsPresent -or -not (Test-Path $ProfileFile)
    if (-not $mustDetect -and (Test-Path $ProfileFile)) {
        $existing = Get-Content $ProfileFile -Raw | ConvertFrom-Json
        if ($existing.torch_profile -eq "cu124") { $mustDetect = $true }
        if ($smi.ok -and $existing.gpu_name -ne $smi.name) { $mustDetect = $true }
        if ($smi.ok -and -not (Test-ProfileMatchesGpu $existing $smi.name)) {
            $mustDetect = $true
            Write-Log "Stale profile ($($existing.torch_profile) vs GPU $($smi.name)); re-detecting" "Yellow"
        }
    }

    if ($Profile) {
        if (-not (Test-Path $ProfileFile)) { Invoke-DetectGpu }
    } elseif ($mustDetect) {
        Invoke-DetectGpu
    }

    if (-not (Test-Path $ProfileFile)) {
        throw "Missing $ProfileFile"
    }

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
            "cpu" {
                $p.torch_index_url = ""
                $p.torch_nightly = $false
            }
        }
    }

    if ($p.torch_profile -eq "cu124") {
        Write-Log "Upgrading saved profile cu124 -> cu130" "Yellow"
        $p.torch_profile = "cu130"
        $p.torch_index_url = "https://download.pytorch.org/whl/cu130"
        $p.torch_nightly = $false
        $p.min_cuda_major = 13
    }

    if (-not $p.comfy_launch_extra -or $p.comfy_launch_extra -eq "--lowvram") {
        $p.comfy_launch_extra = "--lowvram --disable-cuda-malloc"
    }

    if ($smi.ok -and $p.gpu_name -ne $smi.name) {
        $p.gpu_name = $smi.name
        $p.driver_version = $smi.driver
    }

    if ($smi.ok -and -not (Test-ProfileMatchesGpu $p $smi.name)) {
        $fixed = New-GpuProfileObject -GpuName $smi.name -Driver $smi.driver
        Write-Log "Corrected profile to $($fixed.torch_profile) for $($smi.name)" "Yellow"
        $p = $fixed
    }

  return $p
}

function Save-Profile($gpu) {
    $gpu | ConvertTo-Json -Depth 4 | Set-Content -Path $ProfileFile -Encoding UTF8
}

function Invoke-CudaProbe {
    param($gpu)
    Set-ProbeEnv $gpu
    return (Invoke-Py (Join-Path $PSScriptRoot "probe_torch_cuda.py"))
}

function Test-CudaProbe($gpu) {
    return ((Invoke-CudaProbe $gpu) -eq 0)
}

function Report-CudaRuntimeFailure {
    param($gpu, [int]$ProbeCode, [string]$TorchVersion)
    $smi = Get-SmiGpuInfo
    Write-Log "PyTorch wheel OK ($TorchVersion) but CUDA runtime failed (probe exit $ProbeCode)" "Red"
    Write-Log "This is NOT fixed by reinstalling torch - check driver / GPU state." "Yellow"
    if ($smi.lost) {
        Write-Log "nvidia-smi: GPU IS LOST -> reboot PC first." "Red"
        return
    }
    if ($smi.driver) {
        Write-Log "nvidia-smi driver: $($smi.driver) | GPU: $($smi.name)" "Cyan"
    }
    $hint = Get-DriverHintForProfile $gpu.torch_profile
    if ($smi.driver -and -not (Test-DriverForTorchProfile $smi.driver $gpu.torch_profile)) {
        Write-Log $hint "Red"
        Write-Log "Download: https://www.nvidia.com/Download/index.aspx -> install -> reboot" "Yellow"
    } elseif ($ProbeCode -eq 6) {
        Write-Log $hint "Red"
    } else {
        Write-Log "Try: reboot, then .\install\repair_comfyui_cuda.ps1 -ComfyRoot YOUR_COMFY_ROOT" "Yellow"
    }
}

function Get-InstalledTorchVersion {
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $v = (& $PythonExe -c "import torch; print(torch.__version__)" 2>$null | Select-Object -Last 1)
    $ErrorActionPreference = $prev
    return ($v | ForEach-Object { "$_".Trim() })
}

function Install-Torch($gpu, [switch]$UseExtraIndex) {
    Write-Log "pip uninstall torch torchvision torchaudio ..." "Yellow"
    Invoke-Pip @("uninstall", "-y", "torch", "torchvision", "torchaudio") | Out-Null

    $pipArgs = @("install", "--no-cache-dir", "--force-reinstall")
    if ($gpu.torch_nightly) { $pipArgs += "--pre" }

    if ($gpu.torch_profile -eq "cu130") {
        $pipArgs += @("torch==2.10.0", "torchvision==0.25.0", "torchaudio==2.10.0")
    } else {
        $pipArgs += @("torch", "torchvision", "torchaudio")
    }

    if ($UseExtraIndex) {
        $pipArgs += @("--extra-index-url", $gpu.torch_index_url)
    } else {
        $pipArgs += @("--index-url", $gpu.torch_index_url)
    }

    Write-Log "pip install $($gpu.torch_profile) from $($gpu.torch_index_url) ..." "Cyan"
    return (Invoke-Pip $pipArgs) -eq 0
}

Write-Log "=== JinFrame PyTorch install ===" "Cyan"
Write-Log "Python: $PythonExe"

$gpu = Get-GpuProfile
Set-ProbeEnv $gpu
Write-Log "GPU: $($gpu.gpu_name) | profile: $($gpu.torch_profile)" "Cyan"
Write-Log $($gpu.reason) "DarkGray"

$smiPre = Get-SmiGpuInfo
if ($smiPre.ok -and $gpu.torch_profile -ne "cpu") {
    if (-not (Test-DriverForTorchProfile $smiPre.driver $gpu.torch_profile)) {
        Write-Log "Driver $($smiPre.driver) too old for $($gpu.torch_profile). Update to 580+ before ComfyUI will start." "Red"
        Write-Log (Get-DriverHintForProfile $gpu.torch_profile) "Yellow"
    }
}

if ($gpu.torch_profile -eq "cpu") {
    Write-Log "CPU mode - skip CUDA wheels" "Yellow"
    Save-Profile $gpu
    exit 0
}

$ver = Get-InstalledTorchVersion
if ($ver -and (Test-TorchTagMatchesProfile $ver $gpu.torch_profile) -and (Test-CudaProbe $gpu) -and -not $Force) {
    Write-Log "Already OK: $ver" "Green"
    Save-Profile $gpu
    Invoke-Py (Join-Path $PSScriptRoot "probe_torch_cuda.py") | Out-Null
    exit 0
}

if ($ver) {
    Write-Log "Current torch $ver - reinstalling as $($gpu.torch_profile)" "Yellow"
}

$ok = Install-Torch $gpu
if (-not $ok -and $gpu.torch_profile -eq "cu130") {
    Write-Log "Retry cu130 with --extra-index-url ..." "DarkYellow"
    $ok = Install-Torch $gpu -UseExtraIndex
}

$installedVer = Get-InstalledTorchVersion
$wheelOk = $ok -and $installedVer -and (Test-TorchTagMatchesProfile $installedVer $gpu.torch_profile)
if ($wheelOk) {
    $probeCode = Invoke-CudaProbe $gpu
    if ($probeCode -eq 0) {
        Write-Log "SUCCESS: $installedVer" "Green"
        Save-Profile $gpu
        Clear-RebootPending $RepoRoot
        exit 0
    }
    if ((Test-RebootPending $RepoRoot) -and $probeCode -in 1, 5, 6) {
        Write-Log "PyTorch $installedVer OK; CUDA probe skipped (driver reboot pending)" "Yellow"
        Write-Log "Finish install, then reboot and run repair_comfyui_cuda.ps1" "Yellow"
        Save-Profile $gpu
        exit 0
    }
    Report-CudaRuntimeFailure $gpu $probeCode $installedVer
    exit 1
}

$is50 = Test-Rtx50GpuName $gpu.gpu_name
if ($is50 -and $gpu.torch_profile -eq "cu128_nightly") {
    Write-Log "cu128 nightly failed on RTX 50 - trying cu130 last resort ..." "DarkYellow"
    $gpu.torch_profile = "cu130"
    $gpu.torch_index_url = "https://download.pytorch.org/whl/cu130"
    $gpu.torch_nightly = $false
    $gpu.min_cuda_major = 13
    if ((Install-Torch $gpu) -and (Test-CudaProbe $gpu)) {
        Write-Log "Fallback cu130 OK (RTX 50 - may lack sm_120)" "Green"
        Save-Profile $gpu
        exit 0
    }
    Write-Log "cu128 and cu130 both failed on RTX 50" "Red"
} elseif (-not $is50) {
    Write-Log "pip install failed for cu130 on RTX 3050/30/40" "Red"
    Write-Log "Will NOT install cu128 (ComfyUI 0.21+ needs cu130 on 30/40 series)." "Yellow"
} else {
    Write-Log "Install failed for profile $($gpu.torch_profile)" "Red"
}

exit 1
