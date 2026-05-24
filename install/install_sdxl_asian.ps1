# SDXL Base + Asian portrait LoRA (+ optional AWPortrait XL checkpoint)
# Run: C:\ComfyUI\install\install_sdxl_asian.ps1
# Optional: -IncludeAWPortrait  (downloads ~7GB AWPortrait_XL merge)

param([switch]$IncludeAWPortrait)

$ErrorActionPreference = "Stop"
$Python = "C:\ComfyUI\python_embeded\python.exe"
$CkptDir = "C:\ComfyUI\ComfyUI\models\checkpoints"
$LoraDir = "C:\ComfyUI\ComfyUI\models\loras"

$Files = @(
    @{
        Url = "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0_0.9vae.safetensors"
        Path = Join-Path $CkptDir "sd_xl_base_1.0_0.9vae.safetensors"
        MinGB = 6
    },
    @{
        Url = "https://huggingface.co/ntc-ai/SDXL-LoRA-slider.asian/resolve/main/asian.safetensors"
        Path = Join-Path $LoraDir "asian_sd_xl.safetensors"
        MinGB = 0.005
    },
    @{
        Url = "https://huggingface.co/DRDELATV/ASIAN_WOMAN_LORA_SDXL/resolve/main/pytorch_lora_weights.safetensors"
        Path = Join-Path $LoraDir "asian_woman_sd_xl.safetensors"
        MinGB = 0.05
    }
)

if ($IncludeAWPortrait) {
    $Files += @{
        Url = "https://huggingface.co/awplanet/AWPortraitXL/resolve/main/AWPortrait_XL_ver1.1.safetensors"
        Path = Join-Path $CkptDir "AWPortrait_XL_ver1.1.safetensors"
        MinGB = 6.5
    }
}

function Download-File($Url, $Out, $MinGB) {
    New-Item -ItemType Directory -Force -Path (Split-Path $Out) | Out-Null
    if (Test-Path $Out) {
        $gb = (Get-Item $Out).Length / 1GB
        if ($gb -ge $MinGB) {
            Write-Host "[skip] $([IO.Path]::GetFileName($Out)) ($([math]::Round($gb,2)) GB)" -ForegroundColor Yellow
            return
        }
        Remove-Item $Out -Force
    }
    Write-Host "[download] $([IO.Path]::GetFileName($Out))" -ForegroundColor Green
    & $Python -c @"
import shutil, urllib.request
url = r'$Url'
out = r'$Out'
part = out + '.part'
req = urllib.request.Request(url, headers={'User-Agent': 'ComfyUI-sdxl-installer'})
with urllib.request.urlopen(req, timeout=120) as resp, open(part, 'wb') as f:
    total = int(resp.headers.get('content-length', 0))
    done = 0
    while True:
        chunk = resp.read(8 * 1024 * 1024)
        if not chunk:
            break
        f.write(chunk)
        done += len(chunk)
        if total:
            print(f'  {done/total*100:.1f}%', flush=True)
shutil.move(part, out)
print('done')
"@
    if ($LASTEXITCODE -ne 0) { throw "Failed: $Out" }
}

foreach ($f in $Files) { Download-File $f.Url $f.Path $f.MinGB }

Write-Host @"

SDXL ready.
  Base+LoRA workflow: SDXL_Asian_LoRA_国人肖像.json
  AWPortrait workflow: SDXL_AWPortraitXL_国人肖像.json  (needs -IncludeAWPortrait)
"@ -ForegroundColor Cyan
