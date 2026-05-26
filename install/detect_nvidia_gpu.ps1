# Detect NVIDIA GPU and choose PyTorch install profile for this machine.
# RTX 50xx (5060 etc.) -> cu128 nightly (sm_120). RTX 30/40xx (3050, 3060, 4070) -> cu130 (ComfyUI 0.21+).
# Usage:
#   .\install\detect_nvidia_gpu.ps1 -RepoRoot "K:\tiger\jinFrame\jinFrameComfyUI"

param(
    [string]$RepoRoot = "",
    [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"

if (-not $RepoRoot) {
    $RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
}
$RepoRoot = [System.IO.Path]::GetFullPath($RepoRoot)
if (-not $OutFile) {
    $OutFile = Join-Path $RepoRoot "jinframe_gpu_profile.json"
}

function Test-Rtx50Series {
    param([string]$Name)
    # Must NOT match RTX 3050 / 4050 (30xx, 40xx). Only 50xx Blackwell.
    $u = $Name.ToUpperInvariant()
    if ($u -match '\bRTX\s*50[0-9]{2}\b') { return $true }
    if ($u -match '\b(5050|5060|5070|5080|5090)\b') { return $true }
    return $false
}

$profile = @{
    has_nvidia = $false
    gpu_name = ""
    driver_version = ""
    torch_profile = "cpu"
    torch_index_url = ""
    torch_nightly = $false
    comfy_launch_extra = "--cpu"
    min_cuda_major = 13
    reason = ""
    detected_at = (Get-Date).ToString("o")
}

$nvidiaSmi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if (-not $nvidiaSmi) {
    $profile.reason = "nvidia-smi not found; no NVIDIA driver or CPU-only host. Using CPU PyTorch."
    $profile | ConvertTo-Json -Depth 4 | Set-Content -Path $OutFile -Encoding UTF8
    Write-Host "[gpu] NO NVIDIA (nvidia-smi missing) -> CPU mode" -ForegroundColor Yellow
    exit 0
}

try {
    $nameLine = (& nvidia-smi --query-gpu=name --format=csv,noheader 2>$null | Select-Object -First 1).Trim()
    $drvLine = (& nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>$null | Select-Object -First 1).Trim()
} catch {
    $nameLine = ""
    $drvLine = ""
}

if ([string]::IsNullOrWhiteSpace($nameLine)) {
    $profile.reason = "nvidia-smi returned no GPU name."
    $profile | ConvertTo-Json -Depth 4 | Set-Content -Path $OutFile -Encoding UTF8
    Write-Host "[gpu] nvidia-smi failed -> CPU mode" -ForegroundColor Yellow
    exit 0
}

$profile.has_nvidia = $true
$profile.gpu_name = $nameLine
$profile.driver_version = $drvLine
$launchGpu = "--lowvram --disable-cuda-malloc"

if (Test-Rtx50Series -Name $nameLine) {
    $profile.torch_profile = "cu128_nightly"
    $profile.torch_index_url = "https://download.pytorch.org/whl/nightly/cu128"
    $profile.torch_nightly = $true
    $profile.comfy_launch_extra = $launchGpu
    $profile.min_cuda_major = 12
    $profile.reason = "RTX 50 series (e.g. 5060): PyTorch cu128 nightly for sm_120."
} else {
    $profile.torch_profile = "cu130"
    $profile.torch_index_url = "https://download.pytorch.org/whl/cu130"
    $profile.torch_nightly = $false
    $profile.comfy_launch_extra = $launchGpu
    $profile.min_cuda_major = 13
    $profile.reason = "RTX 30/40 series (e.g. 3050, 3060, 4070): PyTorch cu130 for ComfyUI 0.21+."
}

$profile | ConvertTo-Json -Depth 4 | Set-Content -Path $OutFile -Encoding UTF8

Write-Host "[gpu] $($profile.gpu_name)" -ForegroundColor Cyan
Write-Host "[gpu] driver $($profile.driver_version)" -ForegroundColor DarkGray
Write-Host "[gpu] torch profile: $($profile.torch_profile) -> $($profile.torch_index_url)" -ForegroundColor Green
Write-Host "[gpu] launch: $($profile.comfy_launch_extra)" -ForegroundColor Green
Write-Host "[gpu] $($profile.reason)" -ForegroundColor DarkGray
Write-Host "[gpu] saved $OutFile" -ForegroundColor DarkGray
