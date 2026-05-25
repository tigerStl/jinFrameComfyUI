# 模型版本锁定（MODELS.lock.json）

测试通过的模型文件以 **`MODELS.lock.json`** 为唯一标准：固定 Hugging Face **commit**、**文件大小** 与 **SHA256**。  
安装与金帧助手下载均使用锁文件中的 URL，**不再使用** `resolve/main`。

锁定时间：`MODELS.lock.json` 内 `locked_at` 字段。

---

## 第二台电脑：推荐流程

```powershell
# 1. 克隆金帧仓库并进入根目录
$env:COMFYUI_ROOT = "你的ComfyUI路径\ComfyUI"

# 2. 同步工作流
.\install\sync_to_comfyui.ps1

# 3. 按包下载锁定版本（示例：仅 Hunyuan）
python install\download_from_lock.py --pack hunyuan_dit

# 4. 校验
python install\verify_models.py --pack hunyuan_dit
```

全部模型包：

```powershell
python install\download_from_lock.py --all
python install\verify_models.py
```

---

## 从测试机重新生成锁文件

在**已测通**的机器上（模型已在 `COMFYUI_ROOT\models\`）：

```powershell
cd 金帧仓库根目录
python install\generate_models_lock.py --comfy-root "C:\ComfyUI\ComfyUI"
```

会读取 HF 当前 `main` 的 **commit SHA**，并对本机已有文件计算 **SHA256**（以本机文件为准）。  
生成后请 `git add MODELS.lock.json` 并在另一台机 `verify` / `download_from_lock`。

---

## 文件说明

| 文件 | 作用 |
|------|------|
| `MODELS.lock.json` | 锁定清单（提交到 Git） |
| `install/generate_models_lock.py` | 生成/更新锁文件 |
| `install/verify_models.py` | 校验本机 `models\` 是否匹配 |
| `install/download_from_lock.py` | 按锁下载 |
| `install/models_lock.py` | 库：解析锁、校验、合并 manifest |

金帧助手 `registry.py` 会读取同目录仓库下的 `MODELS.lock.json`，下载后自动做 SHA256 校验。

---

## 特殊项

| id | 说明 |
|----|------|
| `ae` | BFL 仓库需 HF 登录；锁文件仅记录本机测过的 **sha256**，请从测试机复制 `vae\ae.safetensors` |
| `ltx_distill_lora` | 无 HF URL；从仓库 `distill_loras\` 复制或本机已有文件 |
| `flux_dev_fp8` | 若 `sha256_mismatch_hf` 存在，表示本机 fp8 与 HF LFS 登记不一致；以锁内 **sha256** 为准 |

---

## 模型包与锁定 id 对照

| 包 id | 文件 id |
|-------|---------|
| `flux_core` | flux_dev_fp8, clip_l, t5xxl_fp8, ae |
| `sdxl_portrait` | awportrait |
| `hunyuan_dit` | hunyuan12 |
| `kolors` | chatglm3 |
| `wan_i2v` | wan_high, wan_low, umt5, wan_vae, wan_lora_h, wan_lora_l |
| `ltx_cloud` | ltx_fp8, gemma_fp4, ltx_distill_lora |
