"""Build LTX-2.3 dev-fp8 cloud GPU workflows from repo templates (API format)."""
import copy
import json
import shutil
import sys
from pathlib import Path

_INST = Path(__file__).resolve().parent
sys.path.insert(0, str(_INST))
from repo_paths import REPO_WF, COMFY_WF  # noqa: E402

WF = REPO_WF
OUT = WF / "ltx云GPU"
COMFY = COMFY_WF / "ltx云GPU"

SOURCES = {
    "LTX23_云GPU_I2V_distilled_fp8.json": WF / "ltx23_i2v distilled.json",
    "LTX23_云GPU_T2V_distilled_fp8.json": WF / "ltx23_t2v distilled.json",
    "LTX23_云GPU_I2V_base_fp8.json": WF / "ltx23_i2v base.json",
    "LTX23_云GPU_T2V_base_fp8.json": WF / "ltx23_t2v base.json",
}

README = """# LTX 2.3 · 云 GPU 流程（dev-fp8）

本目录为 **官方 ComfyUI LTX-2.3 + `ltx-2.3-22b-dev-fp8`**，与本地 8GB 用的 **GGUF + LTX2_SM**（`ltx视频流/`）是两套路线。

## 1. 仅下载模型（不运行）

**Windows**

```powershell
cd c:\\tiger\\videoModel\\jinFrameComfyUI\\install
.\\install_ltx23_dev_fp8_download.ps1 -ComfyRoot "C:\\ComfyUI\\ComfyUI"
```

**Linux 云主机**

```bash
export COMFY_ROOT=/workspace/ComfyUI
bash install/install_ltx23_dev_fp8_download.sh
```

| 文件 | 目录 |
|------|------|
| `ltx-2.3-22b-dev-fp8.safetensors` | `models/checkpoints/` |
| `gemma_3_12B_it_fp4_mixed.safetensors` | `models/text_encoders/` |
| `ltx-2.3-22b-distilled-lora-1.1_fro90_ceil72_condsafe.safetensors` | `models/loras/`（从仓库 `distill_loras/` 复制） |
| `ltx-2.3-spatial-upscaler-x2-1.0.safetensors` | `models/latent_upscale_models/`（T2V 可选） |
| `taeltx2_3.safetensors` | `models/vae/`（T2V 音频 VAE，可选） |

显存建议：**24GB+** 跑 fp8；**48GB** 可开更高分辨率与 spatial upscaler。

## 2. 复原工作流到 ComfyUI

```powershell
python c:\\tiger\\videoModel\\jinFrameComfyUI\\install\\build_ltx23_cloud_workflows.py
```

或手动复制 `workflows/ltx云GPU/` → `ComfyUI/user/default/workflows/ltx云GPU/`。

## 3. 在云上加载（API 格式）

这些 json 为 **ComfyUI API / Prompt 格式**（节点号为 `"1"`, `"2"`…）：

1. ComfyUI 更新到支持 LTX-2.3 的版本（见 [官方文档](https://docs.comfy.org/tutorials/video/ltx/ltx-2-3)）
2. 菜单 **Workflow → Open** 或 **Import**，选择本目录 json  
3. 若提示缺节点：升级 ComfyUI；云镜像选带 **LTX-2.3 核心节点** 的模板  
4. 也可用 **ComfyUI Cloud** 同款模板对照连线

## 4. 本目录相对根模板的修改

| 项目 | 云 GPU 版 |
|------|-----------|
| Sulphur LoRA | **已禁用**（`sulphur_final` strength=0，避免与 distill 冲突） |
| 保存路径 | `video/LTX_cloud/i2v` / `video/LTX_cloud/t2v`（SaveVideo 自动 `_00001_` 递增） |
| 主模型 | 保持 `ltx-2.3-22b-dev-fp8.safetensors` |
| Distill LoRA | `ltx-2.3-22b-distilled-lora-1.1_fro90_ceil72_condsafe.safetensors` |

## 5. 推荐 Queue 顺序

| 顺序 | 文件 | 用途 |
|------|------|------|
| ① | `LTX23_云GPU_I2V_distilled_fp8.json` | 图生视频（distill 步数少，云上单次试跑） |
| ② | `LTX23_云GPU_T2V_distilled_fp8.json` | 文生视频 |
| 备 | `*_base_fp8.json` | 更高步数/质量，耗时长 |

**不要**与 `ltx视频流/`（GGUF）在同一 Queue 里混用节点。

## 6. 云上与本地 8GB 差异

| | 云 GPU | 本地 8GB |
|--|--------|----------|
| 权重 | safetensors fp8 checkpoint | GGUF Q8 + LTX2_SM |
| 启动 | 无需 `--lowvram` | `--lowvram` |
| 分辨率 | 可在 EmptyLTXVLatentVideo / 缩放节点提高到 1280×720 等 | 建议 768×432 |
| 分镜 | 可直接跑长片段或多段 | 建议 FLUX 关键帧 + 短 LTX 拼接 |

## 7. 输出与回传

- 视频：`ComfyUI/output/video/LTX_cloud/...`
- 回传本地：打包 `output/video/LTX_cloud/` 或对象存储同步

## 8. 重建

```powershell
python install\\build_ltx23_cloud_workflows.py
```
"""


def _patch_api_workflow(data: dict, *, save_prefix: str) -> dict:
    data = copy.deepcopy(data)
    if "nodes" in data:
        from sanitize_workflow_prompts import sanitize_canvas_workflow

        sanitize_canvas_workflow(data)
    for node in data.values() if "nodes" not in data else []:
        if not isinstance(node, dict):
            continue
        inp = node.get("inputs")
        if not isinstance(inp, dict):
            continue
        if node.get("class_type") == "SaveVideo" and "filename_prefix" in inp:
            inp["filename_prefix"] = save_prefix
        if node.get("class_type") == "LoraLoaderModelOnly":
            if inp.get("lora_name") == "sulphur_final.safetensors":
                inp["strength_model"] = 0
                meta = node.setdefault("_meta", {})
                meta["title"] = "Sulphur LoRA (OFF cloud)"
    return data


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    mapping = {
        "LTX23_云GPU_I2V_distilled_fp8.json": ("ltx23_i2v distilled.json", "video/LTX_cloud/i2v"),
        "LTX23_云GPU_T2V_distilled_fp8.json": ("ltx23_t2v distilled.json", "video/LTX_cloud/t2v"),
        "LTX23_云GPU_I2V_base_fp8.json": ("ltx23_i2v base.json", "video/LTX_cloud/i2v_base"),
        "LTX23_云GPU_T2V_base_fp8.json": ("ltx23_t2v base.json", "video/LTX_cloud/t2v_base"),
    }
    for out_name, (src_name, prefix) in mapping.items():
        src = WF / src_name
        if not src.exists():
            print("skip missing", src_name)
            continue
        raw = json.loads(src.read_text(encoding="utf-8"))
        patched = _patch_api_workflow(raw, save_prefix=prefix)
        (OUT / out_name).write_text(
            json.dumps(patched, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print("wrote", out_name.encode("unicode_escape").decode())

    (OUT / "README.md").write_text(README, encoding="utf-8")
    (OUT / "00_云GPU复原清单.md").write_text(
        README.split("## 8. 重建")[0].strip() + "\n",
        encoding="utf-8",
    )

    if COMFY.parent.parent.exists():
        COMFY.mkdir(parents=True, exist_ok=True)
        for p in OUT.iterdir():
            if p.is_file():
                shutil.copy2(p, COMFY / p.name)
        print("synced ComfyUI workflows OK")


if __name__ == "__main__":
    main()
