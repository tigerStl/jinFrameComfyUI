# Detect NVIDIA GPU and write jinframe_gpu_profile.json
# RTX 5060/50 -> cu128 nightly | RTX 3050/30/40 -> cu130
# Usage: .\install\detect_nvidia_gpu.ps1 -RepoRoot "K:\tiger\jinFrame\jinFrameComfyUI"

param(
    [string]$RepoRoot = "",
    [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "gpu_common.ps1")

if (-not $RepoRoot) {
    $RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
}
$RepoRoot = [System.IO.Path]::GetFullPath($RepoRoot)
if (-not $OutFile) {
    $OutFile = Join-Path $RepoRoot "jinframe_gpu_profile.json"
}

$smi = Get-SmiGpuInfo
if ($smi.lost) {
    Write-Host "[gpu] CRITICAL: GPU IS LOST - reboot PC, then run nvidia-smi again" -ForegroundColor Red
    exit 2
}

if (-not $smi.ok) {
    $cpu = @{
        has_nvidia         = $false
        gpu_name           = ""
        driver_version     = ""
        torch_profile      = "cpu"
        torch_index_url    = ""
        torch_nightly      = $false
        comfy_launch_extra = "--cpu"
        min_cuda_major     = 0
        reason             = "No NVIDIA GPU or nvidia-smi failed."
        detected_at        = (Get-Date).ToString("o")
    }
    $cpu | ConvertTo-Json -Depth 4 | Set-Content -Path $OutFile -Encoding UTF8
    Write-Host "[gpu] NO NVIDIA -> CPU mode" -ForegroundColor Yellow
    exit 0
}

$profile = New-GpuProfileObject -GpuName $smi.name -Driver $smi.driver
if (-not (Test-DriverForTorchProfile $smi.driver $profile.torch_profile)) {
    $hint = Get-DriverHintForProfile $profile.torch_profile
    Write-Host "[gpu] WARNING: driver $($smi.driver) is below recommended minimum." -ForegroundColor Red
    Write-Host "[gpu] $hint" -ForegroundColor Yellow
    Write-Host "[gpu] Update at https://www.nvidia.com/Download/index.aspx then reboot before ComfyUI." -ForegroundColor Yellow
}
$profile | ConvertTo-Json -Depth 4 | Set-Content -Path $OutFile -Encoding UTF8

Write-Host "[gpu] $($profile.gpu_name)" -ForegroundColor Cyan
Write-Host "[gpu] driver $($profile.driver_version)" -ForegroundColor DarkGray
Write-Host "[gpu] profile $($profile.torch_profile) -> $($profile.torch_index_url)" -ForegroundColor Green
Write-Host "[gpu] launch $($profile.comfy_launch_extra)" -ForegroundColor Green
Write-Host "[gpu] $($profile.reason)" -ForegroundColor DarkGray
Write-Host "[gpu] saved $OutFile" -ForegroundColor DarkGray
