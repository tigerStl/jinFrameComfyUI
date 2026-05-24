# jinFrameComfyUI

ComfyUI 工作流、安装脚本与补丁的**主开发仓库**（每类模型 × 每类流程仅保留一份 canonical 工作流，其余已归档至本地备份目录）。

---

## 目录约定

| 路径 | 说明 |
|------|------|
| **`c:\tiger\videoModel\jinFrameComfyUI`** | 只在这里改工作流 / `install` / 文档 |
| **`C:\ComfyUI\ComfyUI`** | 本机运行；用 `install\sync_to_comfyui.ps1` 同步 |
| **`c:\tiger\videoModels\workflowbackup\jinFrameComfyUI`** | 已精简移出的历史/重复工作流（含多场景、多风格、测试版） |

## 保留的工作流（canonical）

| 模型 / 栈 | 流程 | 文件 |
|-----------|------|------|
| FLUX | T2I 通用 | `workflows/Flux_Sample_T2I.json` |
| FLUX | T2I 风格（清冷） | `workflows/Flux_T2I_风格_清冷高级.json` |
| FLUX | I2I 定妆参考 | `workflows/Flux_I2I_定妆照参考.json` |
| FLUX | I2I 人像写实 | `workflows/FLUX_人像写实化_I2I.json` |
| FLUX | 惊悚场景 T2I | `workflows/Flux_T2I_惊悚_大厅走廊.json` |
| FLUX | 人物场景融合 | `workflows/Flux_人物场景融合_单人.json` |
| SDXL | 国人肖像 T2I | `workflows/SDXL_AWPortraitXL_国人肖像.json` |
| Hunyuan DiT | 中文 T2I | `workflows/HunyuanDiT_T2I_中国风格.json` |
| Hunyuan DiT | 图形合成 I2I | `workflows/HunyuanDiT_图形合成_02_图生图.json` |
| Kolors | 惊悚场景 T2I | `workflows/Kolors_T2I_惊悚_场景.json` |
| Wan 2.2 GGUF | I2V | `workflows/I2V_标准_图生视频_稳态少虚影.json` |
| Wan 2.2 | S2V 有声图生视频 | `workflows/Wan22_S2V_有声图生视频_简版.json` |
| Wan | 分镜片段（示例） | `workflows/wan视频流/02_Wan_片段_A_kf01到kf02.json` |
| LTX 2.3 GGUF 本地 | I2V / T2V | `ltx23_i2v distilled.json` / `ltx23_t2v distilled.json` |
| LTX 2.3 云 GPU fp8 | I2V / T2V | `workflows/ltx云GPU/LTX23_云GPU_*_distilled_fp8.json` |
| LTX | 分镜片段（示例） | `workflows/ltx视频流/02_LTX_片段_A_首尾_kf01到kf02.json` |
| LTX | 首帧模板 | `workflows/LTX_Template_首帧.json` |
| — | 脸部局部亮度后处理 | `workflows/后处理_脸部局部亮度.json` |

更多说明见 `workflows/工作流目录说明.md`。从备份恢复某文件时，复制回 `workflows\` 对应路径即可。

## 同步到 ComfyUI

```powershell
cd c:\tiger\videoModel\jinFrameComfyUI
.\install\sync_to_comfyui.ps1
```

仅工作流：`.\install\sync_to_comfyui.ps1 -WorkflowsOnly`

## 安装与补丁

- 环境：`install\setup_comfyui.ps1`
- LTX 云模型下载：`install\install_ltx23_dev_fp8_download.ps1`
- RTX 50 / xformers：`python install\patch_ltx2_sm_pytorch_attention.py`
- Prompt 安全清理：`python install\sanitize_workflow_prompts.py`

## 再次精简工作流

```powershell
python install\prune_workflows.py --dry-run   # 预览
python install\prune_workflows.py             # 移到 workflowbackup
```

## 环境变量

| 变量 | 默认 |
|------|------|
| `JINFRAME_REPO_ROOT` | 本仓库根 |
| `COMFYUI_ROOT` | `C:\ComfyUI\ComfyUI` |

## 模型权重

`*.safetensors` / `*.gguf` 不纳入 Git（见 `.gitignore`），请用 `install\` 脚本或 Hugging Face 自行下载。

## 远程仓库

<https://github.com/tigerStl/jinFrameComfyUI>

---

# jinFrameComfyUI (English)

Primary repo for **ComfyUI workflows**, install scripts, and patches. After pruning, **one canonical workflow per model stack × task** remains; duplicates and variants live under local backup (not in Git).

## Paths

| Path | Role |
|------|------|
| `c:\tiger\videoModel\jinFrameComfyUI` | Edit workflows / `install` / docs here only |
| `C:\ComfyUI\ComfyUI` | Runtime; sync via `install\sync_to_comfyui.ps1` |
| `c:\tiger\videoModels\workflowbackup\jinFrameComfyUI` | Archived workflows removed during cleanup |

## Canonical workflows

See the table in the Chinese section above (same filenames under `workflows/`). Storyboard folders `wan视频流/` and `ltx视频流/` keep one **segment** example plus `00_分镜流程说明.md`.

## Sync

```powershell
cd c:\tiger\videoModel\jinFrameComfyUI
.\install\sync_to_comfyui.ps1
```

## Tools

- `install\sanitize_workflow_prompts.py` — strip unsafe / explicit positive prompts
- `install\prune_workflows.py` — move non-canonical JSON to `workflowbackup`

## Weights

Large checkpoints are **not** versioned; use install scripts or download from Hugging Face.

## Remote

<https://github.com/tigerStl/jinFrameComfyUI>
