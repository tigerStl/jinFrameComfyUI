# 模型安装说明

本仓库附带 **模型版本清单** `MODELS.lock.json`，用于保证您下载的权重与平台测试时使用的版本一致（固定下载地址与 SHA256 校验）。

清单更新时间见 `MODELS.lock.json` 中的 `locked_at` 字段。

---

## 安装步骤（推荐）

在**本仓库根目录**打开 PowerShell，并将 `COMFYUI_ROOT` 设为您的 ComfyUI 安装路径（文件夹内需包含 `models\`）：

```powershell
$env:COMFYUI_ROOT = "D:\ComfyUI\ComfyUI"   # 按实际路径修改

# 1. 将工作流同步到 ComfyUI 侧栏
.\install\sync_to_comfyui.ps1

# 2. 下载所需模型包（示例：混元 Hunyuan）
python install\download_from_lock.py --pack hunyuan_dit

# 3. 确认文件完整
python install\verify_models.py --pack hunyuan_dit
```

若需安装**全部**清单中的模型：

```powershell
python install\download_from_lock.py --all
python install\verify_models.py
```

也可在 ComfyUI 中打开 **金帧助手**，勾选模型包后使用 **一键下载**（同样按清单中的固定版本拉取）。

---

## 模型包对照表

| 包名（`--pack`） | 适用工作流（示例） | 包含内容 |
|------------------|-------------------|----------|
| `flux_core` | `Flux_Sample_T2I.json` 等 | FLUX 文生图 / 图生图 |
| `sdxl_portrait` | `SDXL_AWPortraitXL_国人肖像.json` | SDXL 国人肖像 |
| `hunyuan_dit` | `HunyuanDiT_T2I_中国风格.json` | 混元 DiT 1.2 |
| `kolors` | `Kolors_T2I_惊悚_场景.json` | Kolors + ChatGLM3（另需安装 Kolors 节点） |
| `wan_i2v` | `I2V_标准_图生视频_稳态少虚影.json` | Wan 2.2 图生视频（8GB） |
| `ltx_cloud` | `ltx云GPU\` 下工作流 | LTX 2.3 云 GPU fp8 |

各文件对应的文件名与 `id`，见 `MODELS.lock.json` 或下表。

| 包 id | 文件 id |
|-------|---------|
| `flux_core` | flux_dev_fp8, clip_l, t5xxl_fp8, ae |
| `sdxl_portrait` | awportrait |
| `hunyuan_dit` | hunyuan12 |
| `kolors` | chatglm3 |
| `wan_i2v` | wan_high, wan_low, umt5, wan_vae, wan_lora_h, wan_lora_l |
| `ltx_cloud` | ltx_fp8, gemma_fp4, ltx_distill_lora |

---

## 常见问题

| 情况 | 处理 |
|------|------|
| `verify` 提示缺少文件 | 执行 `download_from_lock.py` 对应 `--pack`，或检查 `COMFYUI_ROOT` 是否指向正确的 ComfyUI |
| `ae.safetensors` | 部分环境需从已正常出图的电脑复制到 `ComfyUI\models\vae\ae.safetensors`（清单中已记录该校验值） |
| `ltx_distill_lora` | 若仓库内有 `distill_loras\` 目录，运行 `sync_to_comfyui.ps1` 可自动复制到 ComfyUI |
| Kolors 报错缺节点 | 在 ComfyUI-Manager 中安装 **ComfyUI-KwaiKolorsWrapper** |
| Wan 报错缺节点 | 安装 **ComfyUI-GGUF** |

---

## 相关脚本（供查阅）

| 文件 | 作用 |
|------|------|
| `MODELS.lock.json` | 版本清单 |
| `install/download_from_lock.py` | 按清单下载 |
| `install/verify_models.py` | 校验是否安装正确 |
| `install/generate_models_lock.py` | 维护人员更新清单时使用 |
