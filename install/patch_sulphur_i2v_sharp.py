"""Tune Sulphur I2V test workflows for sharper output (repo + optional ComfyUI sync)."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

_INST = Path(__file__).resolve().parent
sys.path.insert(0, str(_INST))
from repo_paths import REPO_ROOT, COMFY_WF, COMFY_MODELS  # noqa: E402

REPO = REPO_ROOT
WF_DIR = REPO / "workflows" / "测试"
SRC = WF_DIR / "Sulphur_I2V_图生视频.json"
SHARP = WF_DIR / "Sulphur_I2V_图生视频_清晰.json"
COMFY = COMFY_WF / "测试"
UPSCALER_NAME = "ltx-2.3-spatial-upscaler-x2-1.0.safetensors"
UPSCALER_DIRS = [COMFY_MODELS / "latent_upscale_models"]


def _has_spatial_upscaler() -> bool:
    for d in UPSCALER_DIRS:
        p = d / UPSCALER_NAME
        if p.is_file() and p.stat().st_size > 1_000_000:
            return True
    return False

NOTE = """## Sulphur 图生视频

### 画面发糊？按优先级改
1. **LTX2_LATENTS 分辨率**：至少 **768×432**（竖图可 **432×768**）。**384×576 仅为省显存，会明显糊**
2. **LTX2_SM_KSampler → spatial_upsampler**：选 **ltx-2.3-spatial-upscaler-x2-1.0**（需已下载到 `models/latent_upscale_models/`），输出约 2× 更清晰
3. **LTX2_SM_Model → gguf**：`sulphur_dev-Q3_K_S` 最省显存但最糊；显存够改 **ltx23-transformer-distill-Q8_0.gguf** 或更高量化 Sulphur
4. **steps**：8 为快采；清晰可 **16–24**（更慢）
5. **LTX2_DECO_VIDEO → tile**：显存够可关 **false** 略减糊块
6. **首帧图**：上传 **≥768px 长边** 的清晰定妆照

启动：`run_sulphur.bat`（`--lowvram`）。Gemma 8GB 建议 **infer_device=cpu**。

### 本文件预设
- 默认版：平衡 8GB
- `_清晰.json`：768×432 + spatial 2× + steps 16（更易 OOM）"""

PRESETS = {
    "default": {
        "latents": [640, 384, 73, 24, 0.88, 0.0, 0.0],
        "ksampler_steps": 12,
        "spatial": "none",
        "tile": True,
        "clip_device": "cpu",
        "save_prefix": "video/sulphur_i2v",
    },
    "sharp": {
        "latents": [768, 432, 73, 24, 0.88, 0.0, 0.0],
        "ksampler_steps": 16,
        "spatial": "ltx-2.3-spatial-upscaler-x2-1.0.safetensors",
        "tile": False,
        "clip_device": "cpu",
        "save_prefix": "video/sulphur_i2v_sharp",
    },
}


def _apply(data: dict, preset: dict) -> dict:
    data = json.loads(json.dumps(data))
    for n in data["nodes"]:
        t = n.get("type")
        w = n.get("widgets_values")
        if t == "LTX2_LATENTS" and isinstance(w, list) and len(w) >= 7:
            n["widgets_values"] = preset["latents"]
        elif t == "LTX2_SM_KSampler" and isinstance(w, list):
            w[0] = preset["ksampler_steps"]
            w[-1] = preset["spatial"]
            n["widgets_values"] = w
        elif t == "LTX2_DECO_VIDEO" and isinstance(w, list):
            n["widgets_values"] = [preset["tile"]]
        elif t == "LTX2_SM_Clip" and isinstance(w, list) and len(w) >= 3:
            w[2] = preset["clip_device"]
            n["widgets_values"] = w
        elif t == "SaveVideo" and isinstance(w, list):
            n["widgets_values"] = [preset["save_prefix"], "auto", "auto"]
        elif t == "Note" and n.get("id") == 200:
            n["widgets_values"] = [NOTE]
    return data


def main() -> None:
    base = json.loads(SRC.read_text(encoding="utf-8"))
    sharp_preset = dict(PRESETS["sharp"])
    if not _has_spatial_upscaler():
        sharp_preset["spatial"] = "none"
        print("WARN: spatial upscaler missing -> sharp workflow uses spatial=none")
    else:
        print("OK: spatial upscaler found")
    SRC.write_text(
        json.dumps(_apply(base, PRESETS["default"]), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    SHARP.write_text(
        json.dumps(_apply(base, sharp_preset), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print("wrote workflows OK")

    if COMFY.parent.exists():
        COMFY.mkdir(parents=True, exist_ok=True)
        for name in (SRC.name, SHARP.name, "README.md"):
            src = WF_DIR / name
            if src.exists():
                shutil.copy2(src, COMFY / name)
        print("synced ComfyUI test workflows")


if __name__ == "__main__":
    main()
