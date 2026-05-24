# Kolors + ComfyUI-KwaiKolorsWrapper (8GB: ChatGLM3 quant4)
# Run: c:\tiger\videoModel\jinFrameComfyUI\install\install_kolors.ps1

$ErrorActionPreference = "Stop"
$ComfyRoot = "C:\ComfyUI\ComfyUI"
$Python = "C:\ComfyUI\python_embeded\python.exe"
$CustomNodes = Join-Path $ComfyRoot "custom_nodes"
$WrapperDir = Join-Path $CustomNodes "ComfyUI-KwaiKolorsWrapper"
$Repo = "c:\tiger\videoModel\jinFrameComfyUI"
$LlmDir = Join-Path $ComfyRoot "models\LLM\checkpoints"
$ChatGlm4 = Join-Path $LlmDir "chatglm3-4bit.safetensors"
$ChatGlm4Url = "https://huggingface.co/Kijai/ChatGLM3-safetensors/resolve/main/chatglm3-4bit.safetensors"

function Ensure-Git {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        throw "git not found. Install Git for Windows first."
    }
}

if (-not (Test-Path $Python)) {
    throw "ComfyUI python not found: $Python"
}

Ensure-Git
New-Item -ItemType Directory -Force -Path $CustomNodes, $LlmDir | Out-Null

if (-not (Test-Path $WrapperDir)) {
    Write-Host "[clone] ComfyUI-KwaiKolorsWrapper" -ForegroundColor Green
    git clone --depth 1 https://github.com/kijai/ComfyUI-KwaiKolorsWrapper.git $WrapperDir
} else {
    Write-Host "[skip] wrapper exists: $WrapperDir" -ForegroundColor Yellow
}

Write-Host "[pip] requirements.txt" -ForegroundColor Green
& $Python -m pip install -r (Join-Path $WrapperDir "requirements.txt") -q
& $Python -m pip install "transformers>=4.38.0" "accelerate" "huggingface_hub" -q

if (-not (Test-Path $ChatGlm4)) {
    Write-Host "[download] ChatGLM3 quant4 (~4GB VRAM text encoder) -> $ChatGlm4" -ForegroundColor Green
    & $Python -c @"
import urllib.request, shutil, os
url = r'$ChatGlm4Url'
out = r'$ChatGlm4'
part = out + '.part'
req = urllib.request.Request(url, headers={'User-Agent': 'ComfyUI-kolors-install'})
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
    if ($LASTEXITCODE -ne 0) { throw "ChatGLM3 download failed" }
} else {
    Write-Host "[skip] ChatGLM3 quant4 already present" -ForegroundColor Yellow
}

Write-Host "[note] Kolors UNet (~16GB) downloads on first Queue via DownloadAndLoadKolorsModel" -ForegroundColor Cyan
Write-Host "       -> $ComfyRoot\models\diffusers\Kolors" -ForegroundColor Cyan

$WfSrc = Join-Path $Repo "workflows\Kolors_日系惊悚"
$WfDst = Join-Path $ComfyRoot "user\default\workflows\Kolors_日系惊悚"
if (Test-Path $WfSrc) {
    New-Item -ItemType Directory -Force -Path $WfDst | Out-Null
    Copy-Item -Recurse -Force "$WfSrc\*" $WfDst
    Write-Host "[sync] workflows -> $WfDst" -ForegroundColor Green
}

Write-Host "`nNext:" -ForegroundColor Cyan
Write-Host "  1. Restart ComfyUI (--lowvram recommended)" -ForegroundColor Cyan
Write-Host "  2. Load: user\default\workflows\Kolors_日系惊悚\Kolors_T2I_惊悚_办公大楼大厅走廊.json" -ForegroundColor Cyan
Write-Host "  3. In Load ChatGLM3 node pick: chatglm3-4bit.safetensors" -ForegroundColor Cyan
