# jinFrameComfyUI 本地 ComfyUI 安装（基于 j9460429/sulphur2-install-notes）
# 用法: .\install\setup_comfyui.ps1
# 可选: .\install\setup_comfyui.ps1 -DownloadGguf   # 额外下载 GGUF Q6_K (~18GB)

param(
    [switch]$DownloadGguf,
    [string]$Quant = "Q6_K"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$ComfyUI = Join-Path $RepoRoot "comfyui\ComfyUI"

Write-Host "Repo:    $RepoRoot"
Write-Host "ComfyUI: $ComfyUI"
Write-Host ""

function Ensure-Repo {
    param([string]$Url, [string]$Path)
    if (Test-Path (Join-Path $Path ".git")) {
        Write-Host "[skip] $Path"
        return
    }
    if (Test-Path $Path) { Remove-Item $Path -Recurse -Force }
    git clone --depth 1 $Url $Path
}

function Link-File {
    param([string]$Target, [string]$Link)
    $Target = (Resolve-Path $Target).Path
    if (Test-Path $Link) { return }
    $dir = Split-Path $Link -Parent
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
    try {
        New-Item -ItemType HardLink -Path $Link -Target $Target | Out-Null
        Write-Host "[link] $(Split-Path $Link -Leaf)"
    } catch {
        cmd /c mklink /H "`"$Link`"" "`"$Target`"" | Out-Null
        Write-Host "[link] $(Split-Path $Link -Leaf) (mklink)"
    }
}

# --- clone（若缺失）---
Ensure-Repo "https://github.com/j9460429/sulphur2-install-notes.git" (Join-Path $RepoRoot "install\sulphur2-install-notes")
Ensure-Repo "https://github.com/comfyanonymous/ComfyUI.git" $ComfyUI
Ensure-Repo "https://github.com/j9460429/ComfyUI_LTX2_SM.git" (Join-Path $ComfyUI "custom_nodes\ComfyUI_LTX2_SM")

# --- pip ---
Write-Host ""
Write-Host "pip install ComfyUI_LTX2_SM requirements..."
python -m pip install -r (Join-Path $ComfyUI "custom_nodes\ComfyUI_LTX2_SM\requirements.txt")

# --- 模型目录 ---
$models = Join-Path $ComfyUI "models"
@("gguf", "loras", "vae", "text_encoders", "diffusion_models", "Sulphur\promptenhancer") | ForEach-Object {
    New-Item -ItemType Directory -Force -Path (Join-Path $models $_) | Out-Null
}

# --- 链接本仓库已有权重（省磁盘）---
Write-Host ""
Write-Host "Linking weights from repo root..."
Link-File (Join-Path $RepoRoot "sulphur_dev_bf16.safetensors") (Join-Path $models "diffusion_models\sulphur_dev_bf16.safetensors")
Link-File (Join-Path $RepoRoot "sulphur_dev_fp8mixed.safetensors") (Join-Path $models "diffusion_models\sulphur_dev_fp8mixed.safetensors")
$distil = Get-ChildItem (Join-Path $RepoRoot "distill_loras\*.safetensors") -ErrorAction SilentlyContinue | Select-Object -First 1
if ($distil) {
    Link-File $distil.FullName (Join-Path $models "loras\$($distil.Name)")
}
$mmproj = Join-Path $RepoRoot "prompt_enhancer\mmproj-BF16.gguf"
if (Test-Path $mmproj) {
    Link-File $mmproj (Join-Path $models "Sulphur\promptenhancer\mmproj-BF16.gguf")
}

# --- 可选：按 install-notes 下载 GGUF / VAE / T5 ---
if ($DownloadGguf) {
    $gguf = Join-Path $models "gguf\sulphur_distil-$Quant.gguf"
    if (-not (Test-Path $gguf)) {
        Write-Host "Downloading GGUF $Quant..."
        curl.exe -L -o $gguf "https://huggingface.co/vantagewithai/Sulphur-2-Base-GGUF/resolve/main/sulphur_distil-$Quant.gguf"
    }
}

$vae = Join-Path $models "vae\ltx_2.3_vae.safetensors"
if (-not (Test-Path $vae)) {
    Write-Host "Downloading LTX 2.3 VAE..."
    curl.exe -L -o $vae "https://huggingface.co/Lightricks/LTX-Video-2.3/resolve/main/vae.safetensors"
}

$t5 = Join-Path $models "text_encoders\ltx_2.3_t5.safetensors"
if (-not (Test-Path $t5)) {
    Write-Host "Downloading LTX 2.3 text encoder..."
    curl.exe -L -o $t5 "https://huggingface.co/Lightricks/LTX-Video-2.3/resolve/main/text_encoder.safetensors"
}

Write-Host ""
Write-Host "Done. Start ComfyUI:"
Write-Host "  cd `"$ComfyUI`""
Write-Host "  python main.py"
Write-Host ""
Write-Host "Smoke test workflow:"
Write-Host "  $RepoRoot\install\sulphur2-install-notes\workflows\sulphur2_t2v_smoke_test.json"
Write-Host "Official workflows in repo:"
Write-Host "  $RepoRoot\workflows\"
