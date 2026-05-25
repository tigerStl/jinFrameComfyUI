# Detect NVIDIA GPU and choose PyTorch install profile for this machine.
# Writes jinframe_gpu_profile.json next to repo root.
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
    $u = $Name.ToUpperInvariant()
    if ($u -match 'RTX\s*5[0-9]{2}') { return $true }
    if ($u -match '\b(5060|5070|5080|5090|5050)\b') { return $true }
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

if (Test-Rtx50Series -Name $nameLine) {
    $profile.torch_profile = "cu128_nightly"
    $profile.torch_index_url = "https://download.pytorch.org/whl/nightly/cu128"
    $profile.torch_nightly = $true
    $profile.comfy_launch_extra = "--lowvram"
    $profile.reason = "RTX 50 series / Blackwell (sm_120): PyTorch cu128 nightly."
} else {
    $profile.torch_profile = "cu124"
    $profile.torch_index_url = "https://download.pytorch.org/whl/cu124"
    $profile.torch_nightly = $false
    $profile.comfy_launch_extra = "--lowvram"
    $profile.reason = "NVIDIA GPU (e.g. RTX 3060/40 series): PyTorch CUDA 12.4 stable cu124."
}

$profile | ConvertTo-Json -Depth 4 | Set-Content -Path $OutFile -Encoding UTF8

Write-Host "[gpu] $($profile.gpu_name)" -ForegroundColor Cyan
Write-Host "[gpu] driver $($profile.driver_version)" -ForegroundColor DarkGray
Write-Host "[gpu] torch profile: $($profile.torch_profile) -> $($profile.torch_index_url)" -ForegroundColor Green
Write-Host "[gpu] $($profile.reason)" -ForegroundColor DarkGray
Write-Host "[gpu] saved $OutFile" -ForegroundColor DarkGray
