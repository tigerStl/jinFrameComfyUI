# Hunyuan DiT 1.2 (Tencent) — single checkpoint, Chinese + English prompts
# Run: C:\ComfyUI\install\install_hunyuan_dit.ps1

$ErrorActionPreference = "Stop"
$Python = "C:\ComfyUI\python_embeded\python.exe"
$OutDir = "C:\ComfyUI\ComfyUI\models\checkpoints\hunyuan_dit_comfyui"
$Out = Join-Path $OutDir "hunyuan_dit_1.2.safetensors"
$Url = "https://huggingface.co/comfyanonymous/hunyuan_dit_comfyui/resolve/main/hunyuan_dit_1.2.safetensors"

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

if (Test-Path $Out) {
    $gb = [math]::Round((Get-Item $Out).Length / 1GB, 2)
    if ($gb -gt 7) {
        Write-Host "[skip] hunyuan_dit_1.2 already exists ($gb GB)" -ForegroundColor Yellow
        exit 0
    }
    Remove-Item $Out -Force
}

Write-Host "[download] Hunyuan DiT 1.2 (~8.2 GB) -> $Out" -ForegroundColor Green
& $Python -c @"
import shutil, urllib.request
url = r'$Url'
out = r'$Out'
part = out + '.part'
req = urllib.request.Request(url, headers={'User-Agent': 'ComfyUI-hunyuan-installer'})
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
if ($LASTEXITCODE -ne 0) { throw "Download failed" }

Write-Host "`nLoad workflow: user\default\workflows\HunyuanDiT_T2I_中国风格.json" -ForegroundColor Cyan
Write-Host "8GB tip: run with --lowvram --cpu-vae" -ForegroundColor Cyan
