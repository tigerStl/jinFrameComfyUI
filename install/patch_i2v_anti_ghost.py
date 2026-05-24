"""Patch Wan I2V workflows: less ghosting + sharper defaults for 8GB."""
from __future__ import annotations

import copy
import json
from pathlib import Path

REPO_WF = Path(__file__).resolve().parents[1] / "workflows"
COMFY_WF = Path(r"C:\ComfyUI\ComfyUI\user\default\workflows")
SRC_NAME = "I2V_标准_图生视频.json"
DST_NAME = "I2V_标准_图生视频_稳态少虚影.json"

SUBGRAPH_TYPE = "296b573f-1e7d-43df-a2df-925fe5e17063"

PROMPT_BALANCED = (
    "Same person and scene as the input image. Keep face identity, outfit, and background unchanged. "
    "Static camera, locked tripod. Very subtle motion only: gentle breathing, slight blink, "
    "minimal head movement, no body turn, no walking. Temporal consistency, single subject, sharp focus."
)

PROMPT_STABLE = (
    "Same person and scene as the input image. Keep face identity, outfit, and background unchanged. "
    "Static locked camera on tripod, no camera movement. "
    "Very subtle motion only: gentle breathing, slight blink, minimal head movement under 15 degrees, "
    "no body turn, no spin, no walking, no fast action. "
    "Temporal consistency, single subject, sharp focus, stable anatomy, cinematic."
)

NEG_GHOST = (
    "ghosting, double exposure, afterimage, motion smear, motion blur trail, duplicate person, "
    "multiple faces, warped body, morphing, flickering, temporal inconsistency, "
    "turn around, spin, rotate body, fast movement, walking away, camera shake"
)

NOTE = """## Wan 2.2 标准图生视频（GGUF · 8GB）

**步骤**：上传首帧 → 填英文 motion（勿写转身/快走）→ Queue → MP4

| 项 | 默认（已调） | 仍糊/重影时 |
|---|---|---|
| 分辨率 | **768×432** | 与首帧同比例；勿拉伸 |
| length | **49**（≈3s@16fps） | 勿用 65+（易重影） |
| Lightning LoRA | **0.65** | 稳态版 **0.6** |
| GGUF | Q3 省显存偏糊 | 显存够换 **Q4_K_S** |

**重影**：用 `I2V_标准_图生视频_稳态少虚影.json` 或把 prompt 改成「呼吸/微动」。

启动：`run_wan.bat` 或 `run_sulphur.bat`（`--lowvram`）"""


def walk_nodes(data: dict, fn) -> None:
    if isinstance(data, dict):
        if "nodes" in data:
            for n in data["nodes"]:
                fn(n)
        if "definitions" in data and "subgraphs" in data["definitions"]:
            for sg in data["definitions"]["subgraphs"]:
                walk_nodes(sg, fn)


def patch_subgraph_node(n: dict, *, lora_strength: float, neg_extra: bool) -> None:
    if n.get("type") == "LoraLoaderModelOnly":
        w = n.get("widgets_values")
        if isinstance(w, list) and len(w) >= 2:
            w[1] = lora_strength
    if n.get("id") == 89 and neg_extra:
        w = n.get("widgets_values")
        if w and isinstance(w[0], str) and "ghosting" not in w[0]:
            w[0] = w[0].rstrip() + ", " + NEG_GHOST


def patch_workflow(data: dict, *, mode: str) -> None:
    if mode == "balanced":
        prompt, w, h, length, lora, title = PROMPT_BALANCED, 768, 432, 49, 0.65, "② Wan 2.2 图生视频 (GGUF)"
        group_title = "Wan I2V 标准 · 减虚影默认"
    else:
        prompt, w, h, length, lora, title = PROMPT_STABLE, 768, 432, 49, 0.6, "② Wan 2.2（稳态少虚影）"
        group_title = "Wan I2V 稳态 · 减轻转身虚影"

    for node in data.get("nodes", []):
        if node.get("type") == SUBGRAPH_TYPE:
            wv = node.get("widgets_values")
            if isinstance(wv, list) and len(wv) >= 4:
                wv[0] = prompt
                wv[1] = w
                wv[2] = h
                wv[3] = length
            node["title"] = title
        if node.get("type") == "MarkdownNote" and mode == "balanced":
            node["widgets_values"] = [NOTE]

    def inner(n):
        patch_subgraph_node(n, lora_strength=lora, neg_extra=True)
        if mode == "stable" and n.get("type") == "MarkdownNote":
            n["widgets_values"] = [
                "## 稳态模板\n- LoRA 0.6 · length 49 · 768×432\n- 禁止 turn/spin/walk"
            ]

    walk_nodes(data, inner)
    data["groups"] = [
        {
            "id": 1,
            "title": group_title,
            "bounding": [-460, 60, 1880, 960],
            "color": "#3a5" if mode == "stable" else "#48a",
            "font_size": 22,
            "flags": {},
        }
    ]


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    src = REPO_WF / SRC_NAME
    if not src.is_file():
        src = COMFY_WF / SRC_NAME
    data = json.loads(src.read_text(encoding="utf-8"))

    balanced = copy.deepcopy(data)
    patch_workflow(balanced, mode="balanced")
    _write(REPO_WF / SRC_NAME, balanced)
    if COMFY_WF.parent.exists():
        _write(COMFY_WF / SRC_NAME, balanced)

    stable = copy.deepcopy(data)
    patch_workflow(stable, mode="stable")
    _write(REPO_WF / DST_NAME, stable)
    if COMFY_WF.parent.exists():
        _write(COMFY_WF / DST_NAME, stable)

    print("patched", SRC_NAME, DST_NAME)


if __name__ == "__main__":
    main()
