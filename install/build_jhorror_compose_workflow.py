"""Build 日系惊悚_人物场景融合 FLUX compose workflows."""
import json
import shutil
import sys
from pathlib import Path

_INST = Path(__file__).resolve().parent
sys.path.insert(0, str(_INST))
from repo_paths import REPO_WF, COMFY_WF  # noqa: E402

REPO = REPO_WF / "日系惊悚_人物场景融合"
COMFY = COMFY_WF / "日系惊悚_人物场景融合"

POS_SINGLE = (
    "Keep the exact same face identity from the person reference, same individual, no face swap.\n"
    "Full-body or medium-wide shot: one person physically present IN the scene reference environment.\n"
    "Japanese psychological horror (J-horror): muted desaturated palette, cold fluorescent or sodium vapor light, "
    "matching shadow direction and color cast on skin as the background.\n"
    "Mundane uncanny location (apartment corridor, office after hours, elevator, bedroom at night). "
    "NOT gory; dread from space and light. Hyperreal cinematic still, 35mm grain, sharp focus on face."
)

POS_MULTI = (
    "Two distinct people from the reference composites, preserve both identities, no merged faces, no duplicate limbs.\n"
    "Both characters physically present in the same scene, natural spacing (conversation distance or staggered in corridor), "
    "shared lighting from the environment reference on all faces and clothing.\n"
    "Japanese psychological horror, muted palette, cinematic medium-wide shot, hyperreal film still.\n"
    "NOT gory; uncanny mundane space. Sharp eyes, consistent perspective, single coherent photograph."
)

NEG = (
    "different person, face swap, identity change, merged faces, extra heads, duplicate body, "
    "gore, blood, torture, anime, cartoon, bright cheerful daylight, text watermark, low quality, "
    "oversaturated, floating people, wrong scale, cutout paste look"
)

NOTE = """## 日系惊悚 · 人物场景融合（FLUX I2I）

### 准备素材
| 槽位 | 文件建议 | 说明 |
|------|----------|------|
| ① 人物 A | `person_a.png` | 定妆/半身/全身，**抠图或纯色底更佳** |
| ② 人物 B | `person_b.png` | **单人模式**：与 A 同图或任意图，并把 **AB 融合=0** |
| ③ 场景 | `scene_ref.png` | 先用 `日系惊悚_场景/` 文生图，或实拍/PS 空景 |

放入 `ComfyUI/input/`。

### 单人
1. 只关心人物 A + 场景
2. **ImageBlend AB** → `blend_factor = 0`（完全忽略 B）
3. 正向 prompt 用「单人」段（已默认）
4. **粗叠 人物+场景** → 0.28~0.38（越大越贴背景）
5. **denoise** → 0.50~0.56（融景；过高脸易变）

### 双人（同一空景）
1. A、B 各一张定妆（尽量同分辨率）
2. **AB 融合** → 0.35~0.48（`overlay` 或 `normal` 试）
3. 改正向 prompt 为「双人」段（见节点标题）
4. **粗叠+场景** 略低（0.26~0.34），**denoise** 0.54~0.60

### 三人及以上
- 先 A+B 出图 → 作为新的「人物 A」
- 再加载 C，AB=0.4、再与场景融（分两次 Queue）
- 或 PS 拼好人物层再单通道 I2I

### 输出
`output/sample/flux_jhorror_compose/`

### 下游
融好的图 → `wan视频流` / `ltx视频流` 的 `keyframe/kf_01.png`
"""


def _flux_compose(
    *,
    filename: str,
    group_title: str,
    positive: str,
    pos_title: str,
    blend_ab: float,
    blend_scene: float,
    denoise: float,
    save_prefix: str,
) -> dict:
    return {
        "id": f"jhorror-compose-{filename}",
        "revision": 0,
        "last_node_id": 99,
        "last_link_id": 22,
        "nodes": [
            {
                "id": 1,
                "type": "UNETLoader",
                "pos": [-900, 40],
                "size": [270, 82],
                "flags": {},
                "order": 1,
                "mode": 0,
                "inputs": [
                    {"name": "unet_name", "type": "COMBO", "widget": {"name": "unet_name"}, "link": None},
                    {"name": "weight_dtype", "type": "COMBO", "widget": {"name": "weight_dtype"}, "link": None},
                ],
                "outputs": [{"name": "MODEL", "type": "MODEL", "links": [1]}],
                "properties": {"Node name for S&R": "UNETLoader"},
                "widgets_values": ["flux1-dev-fp8.safetensors", "default"],
            },
            {
                "id": 2,
                "type": "DualCLIPLoader",
                "pos": [-900, 180],
                "size": [270, 130],
                "flags": {},
                "order": 2,
                "mode": 0,
                "inputs": [
                    {"name": "clip_name1", "type": "COMBO", "widget": {"name": "clip_name1"}, "link": None},
                    {"name": "clip_name2", "type": "COMBO", "widget": {"name": "clip_name2"}, "link": None},
                    {"name": "type", "type": "COMBO", "widget": {"name": "type"}, "link": None},
                    {"name": "device", "type": "COMBO", "widget": {"name": "device"}, "link": None},
                ],
                "outputs": [{"name": "CLIP", "type": "CLIP", "links": [2, 14]}],
                "properties": {"Node name for S&R": "DualCLIPLoader"},
                "widgets_values": ["clip_l.safetensors", "t5xxl_fp8_e4m3fn.safetensors", "flux", "default"],
            },
            {
                "id": 3,
                "type": "VAELoader",
                "pos": [-900, 360],
                "size": [270, 82],
                "flags": {},
                "order": 3,
                "mode": 0,
                "inputs": [{"name": "vae_name", "type": "COMBO", "widget": {"name": "vae_name"}, "link": None}],
                "outputs": [{"name": "VAE", "type": "VAE", "links": [10, 11]}],
                "properties": {"Node name for S&R": "VAELoader"},
                "widgets_values": ["ae.safetensors"],
            },
            {
                "id": 99,
                "type": "MarkdownNote",
                "pos": [-900, -280],
                "size": [520, 300],
                "flags": {},
                "order": 0,
                "mode": 0,
                "inputs": [],
                "outputs": [],
                "title": "使用说明",
                "properties": {},
                "widgets_values": [NOTE],
                "color": "#432",
                "bgcolor": "#1a1a1a",
            },
            {
                "id": 4,
                "type": "CLIPTextEncode",
                "pos": [-480, 40],
                "size": [480, 280],
                "flags": {},
                "order": 6,
                "mode": 0,
                "inputs": [
                    {"name": "clip", "type": "CLIP", "link": 2},
                    {"name": "text", "type": "STRING", "widget": {"name": "text"}, "link": None},
                ],
                "outputs": [{"name": "CONDITIONING", "type": "CONDITIONING", "links": [15]}],
                "properties": {"Node name for S&R": "CLIPTextEncode"},
                "title": pos_title,
                "widgets_values": [positive],
            },
            {
                "id": 12,
                "type": "FluxGuidance",
                "pos": [-480, 340],
                "size": [270, 58],
                "flags": {},
                "order": 7,
                "mode": 0,
                "inputs": [
                    {"name": "conditioning", "type": "CONDITIONING", "link": 15},
                    {"name": "guidance", "type": "FLOAT", "widget": {"name": "guidance"}, "link": None},
                ],
                "outputs": [{"name": "CONDITIONING", "type": "CONDITIONING", "links": [3]}],
                "properties": {"Node name for S&R": "FluxGuidance"},
                "widgets_values": [3.7],
            },
            {
                "id": 5,
                "type": "CLIPTextEncode",
                "pos": [-480, 420],
                "size": [420, 120],
                "flags": {},
                "order": 8,
                "mode": 0,
                "inputs": [
                    {"name": "clip", "type": "CLIP", "link": 14},
                    {"name": "text", "type": "STRING", "widget": {"name": "text"}, "link": None},
                ],
                "outputs": [{"name": "CONDITIONING", "type": "CONDITIONING", "links": [5]}],
                "properties": {"Node name for S&R": "CLIPTextEncode"},
                "title": "负向",
                "widgets_values": [NEG],
            },
            {
                "id": 10,
                "type": "LoadImage",
                "pos": [-920, 520],
                "size": [300, 314],
                "flags": {},
                "order": 0,
                "mode": 0,
                "inputs": [
                    {"name": "image", "type": "COMBO", "widget": {"name": "image"}, "link": None},
                    {"name": "upload", "type": "IMAGEUPLOAD", "widget": {"name": "upload"}, "link": None},
                ],
                "outputs": [
                    {"name": "IMAGE", "type": "IMAGE", "links": [16]},
                    {"name": "MASK", "type": "MASK", "links": None},
                ],
                "properties": {"Node name for S&R": "LoadImage"},
                "title": "① 人物 A（主角色）",
                "widgets_values": ["person_a.png", "image"],
            },
            {
                "id": 11,
                "type": "LoadImage",
                "pos": [-920, 880],
                "size": [300, 314],
                "flags": {},
                "order": 1,
                "mode": 0,
                "inputs": [
                    {"name": "image", "type": "COMBO", "widget": {"name": "image"}, "link": None},
                    {"name": "upload", "type": "IMAGEUPLOAD", "widget": {"name": "upload"}, "link": None},
                ],
                "outputs": [
                    {"name": "IMAGE", "type": "IMAGE", "links": [17]},
                    {"name": "MASK", "type": "MASK", "links": None},
                ],
                "properties": {"Node name for S&R": "LoadImage"},
                "title": "② 人物 B（双人时用；单人请 AB=0）",
                "widgets_values": ["person_b.png", "image"],
            },
            {
                "id": 20,
                "type": "LoadImage",
                "pos": [-920, 1240],
                "size": [300, 314],
                "flags": {},
                "order": 2,
                "mode": 0,
                "inputs": [
                    {"name": "image", "type": "COMBO", "widget": {"name": "image"}, "link": None},
                    {"name": "upload", "type": "IMAGEUPLOAD", "widget": {"name": "upload"}, "link": None},
                ],
                "outputs": [
                    {"name": "IMAGE", "type": "IMAGE", "links": [18]},
                    {"name": "MASK", "type": "MASK", "links": None},
                ],
                "properties": {"Node name for S&R": "LoadImage"},
                "title": "③ 场景参考（空景/惊悚场景 T2I）",
                "widgets_values": ["scene_ref.png", "image"],
            },
            {
                "id": 31,
                "type": "ImageBlend",
                "pos": [-520, 700],
                "size": [340, 130],
                "flags": {},
                "order": 4,
                "mode": 0,
                "inputs": [
                    {"name": "image1", "type": "IMAGE", "link": 16},
                    {"name": "image2", "type": "IMAGE", "link": 17},
                    {"name": "blend_factor", "type": "FLOAT", "widget": {"name": "blend_factor"}, "link": None},
                    {"name": "blend_mode", "type": "COMBO", "widget": {"name": "blend_mode"}, "link": None},
                ],
                "outputs": [{"name": "IMAGE", "type": "IMAGE", "links": [19]}],
                "properties": {"Node name for S&R": "ImageBlend"},
                "title": "④ 人物 A+B 粗叠（单人 blend=0）",
                "widgets_values": [blend_ab, "overlay"],
            },
            {
                "id": 32,
                "type": "ImageBlend",
                "pos": [-520, 900],
                "size": [340, 130],
                "flags": {},
                "order": 5,
                "mode": 0,
                "inputs": [
                    {"name": "image1", "type": "IMAGE", "link": 19},
                    {"name": "image2", "type": "IMAGE", "link": 18},
                    {"name": "blend_factor", "type": "FLOAT", "widget": {"name": "blend_factor"}, "link": None},
                    {"name": "blend_mode", "type": "COMBO", "widget": {"name": "blend_mode"}, "link": None},
                ],
                "outputs": [{"name": "IMAGE", "type": "IMAGE", "links": [20]}],
                "properties": {"Node name for S&R": "ImageBlend"},
                "title": "⑤ 人物层 + 场景粗叠（↑ 越大越贴场景）",
                "widgets_values": [blend_scene, "normal"],
            },
            {
                "id": 13,
                "type": "VAEEncode",
                "pos": [-140, 820],
                "size": [210, 46],
                "flags": {},
                "order": 9,
                "mode": 0,
                "inputs": [
                    {"name": "pixels", "type": "IMAGE", "link": 20},
                    {"name": "vae", "type": "VAE", "link": 10},
                ],
                "outputs": [{"name": "LATENT", "type": "LATENT", "links": [6]}],
                "properties": {"Node name for S&R": "VAEEncode"},
                "widgets_values": [],
            },
            {
                "id": 7,
                "type": "KSampler",
                "pos": [120, 200],
                "size": [315, 474],
                "flags": {},
                "order": 10,
                "mode": 0,
                "inputs": [
                    {"name": "model", "type": "MODEL", "link": 1},
                    {"name": "positive", "type": "CONDITIONING", "link": 3},
                    {"name": "negative", "type": "CONDITIONING", "link": 5},
                    {"name": "latent_image", "type": "LATENT", "link": 6},
                    {"name": "seed", "type": "INT", "widget": {"name": "seed"}, "link": None},
                    {"name": "steps", "type": "INT", "widget": {"name": "steps"}, "link": None},
                    {"name": "cfg", "type": "FLOAT", "widget": {"name": "cfg"}, "link": None},
                    {"name": "sampler_name", "type": "COMBO", "widget": {"name": "sampler_name"}, "link": None},
                    {"name": "scheduler", "type": "COMBO", "widget": {"name": "scheduler"}, "link": None},
                    {"name": "denoise", "type": "FLOAT", "widget": {"name": "denoise"}, "link": None},
                ],
                "outputs": [{"name": "LATENT", "type": "LATENT", "links": [7]}],
                "properties": {"Node name for S&R": "KSampler"},
                "title": "CFG=1 · denoise 融景保脸",
                "widgets_values": [0, "randomize", 28, 1.0, "euler", "simple", denoise],
            },
            {
                "id": 8,
                "type": "VAEDecode",
                "pos": [480, 200],
                "size": [210, 46],
                "flags": {},
                "order": 11,
                "mode": 0,
                "inputs": [
                    {"name": "samples", "type": "LATENT", "link": 7},
                    {"name": "vae", "type": "VAE", "link": 11},
                ],
                "outputs": [{"name": "IMAGE", "type": "IMAGE", "links": [8]}],
                "properties": {"Node name for S&R": "VAEDecode"},
                "widgets_values": [],
            },
            {
                "id": 9,
                "type": "SaveImage",
                "pos": [720, 200],
                "size": [280, 58],
                "flags": {},
                "order": 12,
                "mode": 0,
                "inputs": [
                    {"name": "images", "type": "IMAGE", "link": 8},
                    {"name": "filename_prefix", "type": "STRING", "widget": {"name": "filename_prefix"}, "link": None},
                ],
                "outputs": [],
                "properties": {"Node name for S&R": "SaveImage"},
                "widgets_values": [save_prefix],
            },
        ],
        "links": [
            [1, 1, 0, 7, 0, "MODEL"],
            [2, 2, 0, 4, 0, "CLIP"],
            [14, 2, 0, 5, 0, "CLIP"],
            [15, 4, 0, 12, 0, "CONDITIONING"],
            [3, 12, 0, 7, 1, "CONDITIONING"],
            [5, 5, 0, 7, 2, "CONDITIONING"],
            [6, 13, 0, 7, 3, "LATENT"],
            [7, 7, 0, 8, 0, "LATENT"],
            [8, 8, 0, 9, 0, "IMAGE"],
            [10, 3, 0, 13, 1, "VAE"],
            [11, 3, 0, 8, 1, "VAE"],
            [16, 10, 0, 31, 0, "IMAGE"],
            [17, 11, 0, 31, 1, "IMAGE"],
            [19, 31, 0, 32, 0, "IMAGE"],
            [18, 20, 0, 32, 1, "IMAGE"],
            [20, 32, 0, 13, 0, "IMAGE"],
        ],
        "groups": [
            {
                "id": 1,
                "title": group_title,
                "bounding": [-960, -300, 2100, 1680],
                "color": "#432",
                "font_size": 22,
                "flags": {},
            }
        ],
        "config": {},
        "extra": {
            "ds": {"scale": 0.65, "offset": [1000, 320]},
            "workflow_note": "Scene from 日系惊悚_场景 T2I recommended. ImageBlend resizes to first image size.",
        },
        "version": 0.4,
    }


def main():
    REPO.mkdir(parents=True, exist_ok=True)
    COMFY.mkdir(parents=True, exist_ok=True)

    files = [
        (
            "Flux_人物场景融合_单人.json",
            "FLUX · 日系惊悚 · 单人入景融合",
            "正向 · 单人入景",
            POS_SINGLE,
            0.0,
            0.32,
            0.52,
            "sample/flux_jhorror_compose_single",
        ),
        (
            "Flux_人物场景融合_双人.json",
            "FLUX · 日系惊悚 · 双人同场景融合",
            "正向 · 双人入景",
            POS_MULTI,
            0.42,
            0.30,
            0.56,
            "sample/flux_jhorror_compose_dual",
        ),
        (
            "Flux_人物场景融合_主流程.json",
            "FLUX · 日系惊悚 · 人物场景融合（可调单人/双人）",
            "正向 · 默认单人（双人请改文案或打开双人 json）",
            POS_SINGLE,
            0.0,
            0.32,
            0.52,
            "sample/flux_jhorror_compose",
        ),
    ]

    for fname, group, ptitle, pos, ab, sc, dn, prefix in files:
        data = _flux_compose(
            filename=fname.replace(".json", ""),
            group_title=group,
            positive=pos,
            pos_title=ptitle,
            blend_ab=ab,
            blend_scene=sc,
            denoise=dn,
            save_prefix=prefix,
        )
        text = json.dumps(data, ensure_ascii=False, indent=2)
        (REPO / fname).write_text(text, encoding="utf-8")
        (COMFY / fname).write_text(text, encoding="utf-8")

    readme = REPO / "README.md"
    if readme.exists():
        shutil.copy(readme, COMFY / "README.md")
    print("ok")


if __name__ == "__main__":
    main()
