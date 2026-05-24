# Download FLUX.1 Schnell FP8 UNet (~12GB). Reuses existing clip_l, t5xxl_fp8, ae.
# Run: C:\ComfyUI\install\install_flux_schnell_fp8.ps1
# Dev and Schnell can coexist (both ~11GB each).

param([switch]$Force)

$ErrorActionPreference = "Stop"
$Python = "C:\ComfyUI\python_embeded\python.exe"
$Out = "C:\ComfyUI\ComfyUI\models\diffusion_models\flux1-schnell-fp8.safetensors"
$Url = "https://huggingface.co/Comfy-Org/flux1-schnell/resolve/main/flux1-schnell-fp8.safetensors"

New-Item -ItemType Directory -Force -Path (Split-Path $Out) | Out-Null

if ((Test-Path $Out) -and -not $Force) {
    $sz = [math]::Round((Get-Item $Out).Length / 1GB, 2)
    if ($sz -gt 10) {
        Write-Host "[skip] flux1-schnell-fp8 already exists ($sz GB)" -ForegroundColor Yellow
        exit 0
    }
    Remove-Item $Out -Force
}

Write-Host "[download] FLUX.1 Schnell FP8 -> $Out" -ForegroundColor Green
& $Python -c @"
import shutil, urllib.request
url = r'$Url'
out = r'$Out'
part = out + '.part'
req = urllib.request.Request(url, headers={'User-Agent': 'ComfyUI-flux-schnell-installer'})
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
            print(f'  {done/total*100:.1f}% ({done//(1024**3)}GB/{total//(1024**3)}GB)', flush=True)
shutil.move(part, out)
print('done', out)
"@
if ($LASTEXITCODE -ne 0) { throw "Download failed" }

Write-Host "`nFLUX Schnell FP8 ready." -ForegroundColor Cyan
Write-Host "Workflow: user\default\workflows\Flux_Text2Image_Schnell.json" -ForegroundColor Cyan
Write-Host "Schnell: FluxGuidance 3.5 + KSampler CFG 1.0, steps 4" -ForegroundColor Cyan
