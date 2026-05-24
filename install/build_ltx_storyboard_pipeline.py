"""Build ltx视频流: FLUX keyframes + LTX segment workflows + optional 3-frame batch."""
import copy
import json
import shutil
import sys
import uuid
from pathlib import Path

_INST = Path(__file__).resolve().parent
sys.path.insert(0, str(_INST))
from repo_paths import REPO_WF, COMFY_WF  # noqa: E402
OUT = COMFY_WF / "ltx视频流"
REPO_OUT = REPO_WF / "ltx视频流"
WAN_OUT = REPO_WF / "wan视频流"

def _tpl(name: str) -> Path:
    p = REPO_WF / name
    return p if p.exists() else COMFY_WF / name


TPL_FIRST = _tpl("LTX_Template_首帧.json")
TPL_START = _tpl("LTX_Template_起始帧.json")
TPL_END = _tpl("LTX_Template_尾帧.json")

LTX_LORA = "ltx-2.3-22b-distilled-lora-1.1_fro90_ceil72_condsafe.safetensors"

PROMPT_AB = (
    "Interpolate from the first reference to the second reference. "
    "Same person, outfit, and scene. Smooth gradual body turn toward the end pose, "
    "no jump cut, no duplicate limbs, stable face identity, cinematic J-horror lighting."
)
PROMPT_BC = (
    "Continue the turn from the first reference toward the profile in the second reference. "
    "Smooth motion, same wardrobe and background, temporal consistency, sharp focus."
)
PROMPT_STILL = (
    "Same person and scene as the input image. Keep face, outfit, and background identical. "
    "Only subtle motion: breathing, slight eye movement, minimal drift. No scene change."
)
PROMPT_THREE = (
    "Video follows three keyframe references: start at frame zero matching the first image, "
    "middle section aligns with the center reference, ending matches the last reference. "
    "Smooth continuous turn, stable identity, no warping."
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _save(name: str, data: dict) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2)
    (OUT / name).write_text(text, encoding="utf-8")
    (REPO_OUT / name).write_text(text, encoding="utf-8")


def patch_ltx_common(data: dict, *, group_title: str, note: str) -> dict:
    data = copy.deepcopy(data)
    data["id"] = str(uuid.uuid4())
    for n in data.get("nodes", []):
        if n.get("type") == "LTX2_SM_Model":
            w = n.get("widgets_values") or []
            if len(w) >= 3:
                w[2] = LTX_LORA
        if n.get("type") == "MarkdownNote":
            n["widgets_values"] = [note]
    data["groups"] = [
        {
            "id": 1,
            "title": group_title,
            "bounding": [-430, 120, 2800, 1100],
            "color": "#3f789e",
            "font_size": 22,
            "flags": {},
        }
    ]
    return data


def make_tail(
    fname: str,
    title: str,
    start: str,
    end: str,
    prefix: str,
    prompt: str,
    seed: int,
    note: str,
) -> None:
    d = patch_ltx_common(_load(TPL_END), group_title=f"LTX 分镜 · {title}", note=note)
    for n in d["nodes"]:
        props = n.get("properties", {}).get("Node name for S&R", "")
        if n.get("type") == "LoadImage" and props == "Load_StartFrame":
            n["title"] = f"① 首帧 {start}"
            n["widgets_values"] = [start, "image"]
        if n.get("type") == "LoadImage" and props == "Load_EndFrame":
            n["title"] = f"② 尾帧 {end}"
            n["widgets_values"] = [end, "image"]
        if n.get("type") == "SaveVideo":
            n["widgets_values"] = [prefix, "auto", "auto"]
        if n.get("type") == "LTX2_SM_ENCODER":
            w = n.get("widgets_values") or []
            if len(w) >= 7:
                w[6] = prompt
        if n.get("type") == "LTX2_SM_KSampler":
            w = n.get("widgets_values") or []
            if w:
                w[0] = 24
                w[1] = seed
        if n.get("type") == "LTX2_LATENTS":
            w = n.get("widgets_values") or []
            if len(w) >= 5:
                w[0], w[1], w[2], w[3], w[4] = 768, 432, 73, 24, 0.85
    _save(fname, d)


def make_first(
    fname: str,
    title: str,
    image: str,
    prefix: str,
    prompt: str,
    seed: int,
    note: str,
) -> None:
    d = patch_ltx_common(_load(TPL_FIRST), group_title=f"LTX 分镜 · {title}", note=note)
    for n in d["nodes"]:
        if n.get("type") == "LoadImage":
            n["title"] = f"首帧 {image}"
            n["widgets_values"] = [image, "image"]
        if n.get("type") == "SaveVideo":
            n["widgets_values"] = [prefix, "auto", "auto"]
        if n.get("type") == "LTX2_SM_Model":
            w = n.get("widgets_values") or []
            if len(w) >= 5:
                w[4] = "distilled"
        if n.get("type") == "LTX2_SM_ENCODER":
            w = n.get("widgets_values") or []
            if len(w) >= 7:
                w[6] = prompt
        if n.get("type") == "LTX2_SM_KSampler":
            w = n.get("widgets_values") or []
            if w:
                w[0] = 8
                w[1] = seed
        if n.get("type") == "LTX2_LATENTS":
            w = n.get("widgets_values") or []
            if len(w) >= 5:
                w[0], w[1], w[2], w[3], w[4] = 768, 432, 41, 24, 0.74
    _save(fname, d)


def make_three_frame(fname: str, note: str) -> None:
    """Tail template + third LoadImage + chained ImageBatch (kf01,kf02)->batch with kf03."""
    d = patch_ltx_common(_load(TPL_END), group_title="LTX 三关键帧 · 起中尾一次生成", note=note)
    max_id = max(n["id"] for n in d["nodes"])
    max_link = max(lk[0] for lk in d["links"])

    load3 = {
        "id": max_id + 1,
        "type": "LoadImage",
        "pos": [-400, 920],
        "size": [283, 314],
        "flags": {},
        "order": 7,
        "mode": 0,
        "inputs": [
            {"name": "image", "type": "COMBO", "widget": {"name": "image"}, "link": None},
            {"name": "upload", "type": "IMAGEUPLOAD", "widget": {"name": "upload"}, "link": None},
        ],
        "outputs": [
            {"name": "IMAGE", "type": "IMAGE", "links": [max_link + 1]},
            {"name": "MASK", "type": "MASK", "links": None},
        ],
        "properties": {"Node name for S&R": "Load_MidFrame"},
        "title": "③ 中帧 keyframe/kf_02.png",
        "widgets_values": ["keyframe/kf_02.png", "image"],
    }
    batch2 = {
        "id": max_id + 2,
        "type": "ImageBatch",
        "pos": [-80, 720],
        "size": [210, 46],
        "flags": {},
        "order": 8,
        "mode": 0,
        "inputs": [
            {"name": "image1", "type": "IMAGE", "link": max_link + 2},
            {"name": "image2", "type": "IMAGE", "link": max_link + 1},
        ],
        "outputs": [{"name": "IMAGE", "type": "IMAGE", "links": [max_link + 3]}],
        "properties": {"Node name for S&R": "Batch_All_Three"},
        "widgets_values": [],
    }

    for n in d["nodes"]:
        if n.get("type") == "ImageBatch" and n.get("id") == 20:
            batch1_out = n["outputs"][0]["links"][0]
        if n.get("properties", {}).get("Node name for S&R") == "Load_StartFrame":
            n["title"] = "① 首帧 keyframe/kf_01.png"
            n["widgets_values"] = ["keyframe/kf_01.png", "image"]
            load_start_link = n["outputs"][0]["links"][0]
        if n.get("properties", {}).get("Node name for S&R") == "Load_EndFrame":
            n["title"] = "④ 尾帧 keyframe/kf_03.png"
            n["widgets_values"] = ["keyframe/kf_03.png", "image"]
            load_end_link = n["outputs"][0]["links"][0]
        if n.get("type") == "SaveVideo":
            n["widgets_values"] = ["video/ltx_storyboard/seg_all_three", "auto", "auto"]
        if n.get("type") == "LTX2_SM_ENCODER":
            w = n.get("widgets_values") or []
            if len(w) >= 7:
                w[6] = PROMPT_THREE
        if n.get("type") == "LTX2_LATENTS":
            w = n.get("widgets_values") or []
            if len(w) >= 3:
                w[2] = 97

    d["nodes"].append(load3)
    d["nodes"].append(batch2)

    for n in d["nodes"]:
        if n.get("id") == 20:
            n["outputs"][0]["links"] = [max_link + 2]
        if n.get("type") == "LTX2_LATENTS":
            for inp in n.get("inputs", []):
                if inp.get("name") == "image":
                    inp["link"] = max_link + 3
        if n.get("type") == "LTX2_SM_ENCODER":
            for inp in n.get("inputs", []):
                if inp.get("name") == "images":
                    inp["link"] = max_link + 3

    d["links"] = [lk for lk in d["links"] if lk[0] not in (17, 18)]
    d["links"].append([max_link + 1, max_id + 1, 0, max_id + 2, 1, "IMAGE"])
    d["links"].append([max_link + 2, 20, 0, max_id + 2, 0, "IMAGE"])
    d["links"].append([max_link + 3, max_id + 2, 0, 4, 2, "IMAGE"])
    d["links"].append([max_link + 3, max_id + 2, 0, 12, 1, "IMAGE"])

    d["last_node_id"] = max_id + 2
    d["last_link_id"] = max_link + 3
    _save(fname, d)


def copy_flux_keyframes():
    src = WAN_OUT / "01_FLUX_关键帧_三连图.json"
    if not src.exists():
        return
    for dest in (OUT, REPO_OUT):
        shutil.copy(src, dest / "01_FLUX_关键帧_三连图.json")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    REPO_OUT.mkdir(parents=True, exist_ok=True)

    copy_flux_keyframes()

    make_tail(
        "02_LTX_片段_A_首尾_kf01到kf02.json",
        "A: kf01→kf02",
        "keyframe/kf_01.png",
        "keyframe/kf_02.png",
        "video/ltx_storyboard/seg_A",
        PROMPT_AB,
        201,
        "## 片段 A\n首尾帧模式 keyframe，约 3s@24fps（73 帧）。\n复制 `output/keyframe/` → `input/keyframe/`。",
    )
    make_tail(
        "02_LTX_片段_B_首尾_kf02到kf03.json",
        "B: kf02→kf03",
        "keyframe/kf_02.png",
        "keyframe/kf_03.png",
        "video/ltx_storyboard/seg_B",
        PROMPT_BC,
        202,
        "## 片段 B\n第二段转身；显存紧可先跑 A 再单独跑 B。",
    )
    make_first(
        "02_LTX_单帧_稳态_kf03.json",
        "C: kf03 定帧",
        "keyframe/kf_03.png",
        "video/ltx_storyboard/seg_C",
        PROMPT_STILL,
        203,
        "## 末镜微动\ndistilled 单图，steps=8，约 1.7s。可选。",
    )
    make_first(
        "02_LTX_开场_稳态_kf01.json",
        "开场: kf01",
        "keyframe/kf_01.png",
        "video/ltx_storyboard/seg_open",
        PROMPT_STILL,
        200,
        "## 开场定帧\n在 A 之前先稳 1 秒，或替代片段 A 的预览。",
    )

    src_start = TPL_START if TPL_START.exists() else TPL_FIRST
    d = patch_ltx_common(
        _load(src_start),
        group_title="LTX 起始帧 · kf01 锁定第 0 帧",
        note="## 起始帧模式\n锁定第 0 帧后允许后续运动；适合「从正面拉开」单段，不等同于首尾补间。",
    )
    for n in d["nodes"]:
        if n.get("type") == "LoadImage":
            n["widgets_values"] = ["keyframe/kf_01.png", "image"]
            n["title"] = "起始帧 keyframe/kf_01.png"
        if n.get("type") == "SaveVideo":
            n["widgets_values"] = ["video/ltx_storyboard/seg_start_mode", "auto", "auto"]
        if n.get("type") == "LTX2_SM_Model":
            w = n.get("widgets_values") or []
            if len(w) >= 5:
                w[4] = "keyframe"
    _save("02_LTX_起始帧_锁定kf01.json", d)

    make_three_frame(
        "03_LTX_三关键帧_起中尾_一次.json",
        "## 三帧一次（实验）\n"
        "LTX 映射：第 0 帧 + 中间 + 最后一帧。显存与时间更高；8GB 建议用 02_A + 02_B 分段。\n"
        "kf_01 / kf_02 / kf_03 经双次 ImageBatch 送入。",
    )

    for name in ("00_分镜流程说明.md", "concat_segments.ps1", "LTX_模型与模板对照.md"):
        src = REPO_OUT / name
        if src.exists():
            shutil.copy(src, OUT / name)

    print("built ok")


if __name__ == "__main__":
    main()
