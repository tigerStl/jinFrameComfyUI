# LTX-2.3 dev-fp8 model download ONLY (no ComfyUI run, no Queue).
# Usage:
#   .\install_ltx23_dev_fp8_download.ps1
#   .\install_ltx23_dev_fp8_download.ps1 -ComfyRoot "D:\ComfyUI\ComfyUI"
#   .\install_ltx23_dev_fp8_download.ps1 -SkipUpscaler -SkipOptionalVae

param(
    [string]$ComfyRoot = "C:\ComfyUI\ComfyUI",
    [string]$RepoRoot = "c:\tiger\videoModel\jinFrameComfyUI",
    [switch]$SkipUpscaler,
    [switch]$SkipOptionalVae,
    [switch]$UseOfficialDistillLora,
    [switch]$SkipDownload
)

$ErrorActionPreference = "Stop"
$Python = Join-Path (Split-Path $ComfyRoot -Parent) "python_embeded\python.exe"
if (-not (Test-Path $Python)) {
    $Python = "python"
}

$CkptDir = Join-Path $ComfyRoot "models\checkpoints"
$TeDir = Join-Path $ComfyRoot "models\text_encoders"
$LoraDir = Join-Path $ComfyRoot "models\loras"
$UpscaleDir = Join-Path $ComfyRoot "models\latent_upscale_models"
$VaeDir = Join-Path $ComfyRoot "models\vae"

$DistillRepo = Join-Path $RepoRoot "distill_loras\ltx-2.3-22b-distilled-lora-1.1_fro90_ceil72_condsafe.safetensors"
$DistillName = "ltx-2.3-22b-distilled-lora-1.1_fro90_ceil72_condsafe.safetensors"
$OfficialLoraName = "ltx-2.3-22b-distilled-lora-384.safetensors"

$Files = @(
    @{
        Url = "https://huggingface.co/Lightricks/LTX-2.3-fp8/resolve/main/ltx-2.3-22b-dev-fp8.safetensors"
        Path = Join-Path $CkptDir "ltx-2.3-22b-dev-fp8.safetensors"
        MinGB = 20
    },
    @{
        Url = "https://huggingface.co/Comfy-Org/ltx-2/resolve/main/split_files/text_encoders/gemma_3_12B_it_fp4_mixed.safetensors"
        Path = Join-Path $TeDir "gemma_3_12B_it_fp4_mixed.safetensors"
        MinGB = 8
    }
)

if (-not $SkipUpscaler) {
    $Files += @{
        Url = "https://huggingface.co/Lightricks/LTX-2.3/resolve/main/ltx-2.3-spatial-upscaler-x2-1.0.safetensors"
        Path = Join-Path $UpscaleDir "ltx-2.3-spatial-upscaler-x2-1.0.safetensors"
        MinGB = 0.05
    }
}

if (-not $SkipOptionalVae) {
    $Files += @{
        Url = "https://huggingface.co/Kijai/LTX2.3_comfy/resolve/main/vae/taeltx2_3.safetensors"
        Path = Join-Path $VaeDir "taeltx2_3.safetensors"
        MinGB = 0.01
    }
}

if ($UseOfficialDistillLora) {
    $Files += @{
        Url = "https://huggingface.co/Lightricks/LTX-2.3/resolve/main/ltx-2.3-22b-distilled-lora-384.safetensors"
        Path = Join-Path $LoraDir $OfficialLoraName
        MinGB = 0.1
    }
}

function Download-File($Url, $Out, $MinGB) {
    New-Item -ItemType Directory -Force -Path (Split-Path $Out) | Out-Null
    if (Test-Path $Out) {
        $gb = [math]::Round((Get-Item $Out).Length / 1GB, 2)
        if ($gb -ge $MinGB) {
            Write-Host "[skip] $([IO.Path]::GetFileName($Out)) ($gb GB)" -ForegroundColor Yellow
            return
        }
        Remove-Item $Out -Force
    }
    if ($SkipDownload) {
        Write-Host "[dry-run] would download -> $Out" -ForegroundColor Cyan
        return
    }
    Write-Host "[download] $([IO.Path]::GetFileName($Out))" -ForegroundColor Green
    & $Python -c @"
import urllib.request, os, shutil
url = r'$Url'
out = r'$Out'
part = out + '.part'
if os.path.isfile(part):
    os.remove(part)
urllib.request.urlretrieve(url, part)
shutil.move(part, out)
print('done', out)
"@
}

Write-Host "=== LTX-2.3 dev-fp8 download (no run) ===" -ForegroundColor Cyan
Write-Host "ComfyRoot: $ComfyRoot"

foreach ($f in $Files) {
    Download-File $f.Url $f.Path $f.MinGB
}

if (-not $UseOfficialDistillLora) {
    New-Item -ItemType Directory -Force -Path $LoraDir | Out-Null
    $dst = Join-Path $LoraDir $DistillName
    if (Test-Path $DistillRepo) {
        if (-not (Test-Path $dst) -or ((Get-Item $dst).Length -ne (Get-Item $DistillRepo).Length)) {
            Copy-Item -Force $DistillRepo $dst
            Write-Host "[copy] distill LoRA from repo -> $dst" -ForegroundColor Green
        } else {
            Write-Host "[skip] $DistillName (from repo)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "[warn] missing repo LoRA: $DistillRepo" -ForegroundColor Red
        Write-Host "       run with -UseOfficialDistillLora or place file manually in $LoraDir" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "Next (manual):" -ForegroundColor Cyan
Write-Host "  1. Update ComfyUI to nightly/stable with LTX-2.3 core nodes"
Write-Host "  2. Copy workflows\ltx云GPU\ -> user\default\workflows\ltx云GPU\"
Write-Host "  3. python install\build_ltx23_cloud_workflows.py"
Write-Host "  4. Load LTX23_* json on cloud GPU (API format import)"
