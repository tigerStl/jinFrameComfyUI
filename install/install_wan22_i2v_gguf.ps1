# Wan 2.2 I2V GGUF for 8GB VRAM (RTX 5060 class GPUs)
# Run: C:\ComfyUI\install\install_wan22_i2v_gguf.ps1
# Optional: -Quant Q4_K_S  (better quality, needs ~10GB+ VRAM peak)

param(
    [ValidateSet("Q2_K", "Q3_K_S", "Q3_K_M", "Q4_K_S", "Q4_K_M")]
    [string]$Quant = "Q3_K_S",
    [switch]$SkipDownload
)

$ErrorActionPreference = "Stop"
$Python = "C:\ComfyUI\python_embeded\python.exe"
$ComfyRoot = "C:\ComfyUI\ComfyUI"
$UnetDir = "$ComfyRoot\models\unet"
$TeDir = "$ComfyRoot\models\text_encoders"
$VaeDir = "$ComfyRoot\models\vae"
$GgufNode = "$ComfyRoot\custom_nodes\ComfyUI-GGUF"

$HighName = "wan2.2_i2v_high_noise_14B_$Quant.gguf"
$LowName = "wan2.2_i2v_low_noise_14B_$Quant.gguf"
$TeName = "umt5-xxl-encoder-Q4_K_S.gguf"
$VaeName = "wan_2.1_vae.safetensors"
$LoraDir = "$ComfyRoot\models\loras"
$LoraHigh = "wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors"
$LoraLow = "wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors"

$Files = @(
    @{
        Url = "https://huggingface.co/bullerwins/Wan2.2-I2V-A14B-GGUF/resolve/main/$HighName"
        Path = Join-Path $UnetDir $HighName
    },
    @{
        Url = "https://huggingface.co/bullerwins/Wan2.2-I2V-A14B-GGUF/resolve/main/$LowName"
        Path = Join-Path $UnetDir $LowName
    },
    @{
        Url = "https://huggingface.co/city96/umt5-xxl-encoder-gguf/resolve/main/$TeName"
        Path = Join-Path $TeDir $TeName
    },
    @{
        Url = "https://huggingface.co/Comfy-Org/Wan_2.1_ComfyUI_repackaged/resolve/main/split_files/vae/wan_2.1_vae.safetensors"
        Path = Join-Path $VaeDir $VaeName
    },
    @{
        Url = "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/loras/$LoraHigh"
        Path = Join-Path $LoraDir $LoraHigh
    },
    @{
        Url = "https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_Repackaged/resolve/main/split_files/loras/$LoraLow"
        Path = Join-Path $LoraDir $LoraLow
    }
)

function Ensure-GgufNode {
    if (-not (Test-Path $GgufNode)) {
        Write-Host "[git] Cloning ComfyUI-GGUF..." -ForegroundColor Green
        Push-Location (Join-Path $ComfyRoot "custom_nodes")
        git clone --depth 1 https://github.com/city96/ComfyUI-GGUF.git
        Pop-Location
    }
    Write-Host "[pip] ComfyUI-GGUF requirements" -ForegroundColor Green
    & $Python -s -m pip install -r "$GgufNode\requirements.txt" -q
}

function Download-File($Url, $Out) {
    New-Item -ItemType Directory -Force -Path (Split-Path $Out) | Out-Null
    if (Test-Path $Out) {
        $gb = [math]::Round((Get-Item $Out).Length / 1GB, 2)
        if ($gb -gt 0.2) {
            Write-Host "[skip] $([IO.Path]::GetFileName($Out)) ($gb GB)" -ForegroundColor Yellow
            return
        }
        Remove-Item $Out -Force
    }
    Write-Host "[download] $([IO.Path]::GetFileName($Out))" -ForegroundColor Green
    & $Python -c @"
import os, shutil, urllib.request
url = r'$Url'
out = r'$Out'
part = out + '.part'
req = urllib.request.Request(url, headers={'User-Agent': 'ComfyUI-wan-installer'})
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
    if ($LASTEXITCODE -ne 0) { throw "Download failed: $Out" }
}

Ensure-GgufNode
foreach ($d in @($UnetDir, $TeDir, $VaeDir, $LoraDir)) {
    New-Item -ItemType Directory -Force -Path $d | Out-Null
}

if (-not $SkipDownload) {
    foreach ($f in $Files) {
        Download-File $f.Url $f.Path
    }
}

Write-Host "`n[patch] Building GGUF workflow JSON..." -ForegroundColor Cyan
& $Python "$PSScriptRoot\patch_wan22_gguf_workflow.py" --quant $Quant

Write-Host @"

=== Wan 2.2 I2V GGUF ready ===
1. Start: C:\ComfyUI\run_wan.bat  (or run_sulphur.bat — same flags)
2. Load workflow:
   $ComfyRoot\user\default\workflows\Wan22_I2V_GGUF_8GB.json
3. Upload start image + prompt, Queue Prompt

Settings for 8GB:
  - Resolution: 832x480 or 640x480
  - Length: 49-65 frames
  - Quant: $Quant (change with -Quant Q4_K_S if you have headroom)

Models:
  unet: $HighName
        $LowName
  TE:   $TeName
  VAE:  $VaeName

If OOM: close other apps, use -Quant Q2_K, or add --novram to bat file.
"@ -ForegroundColor Cyan
