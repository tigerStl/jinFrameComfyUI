"""Build 人像写实化 FLUX/SDXL I2I workflows + README."""
import json
import shutil
import sys
from pathlib import Path

_INST = Path(__file__).resolve().parent
sys.path.insert(0, str(_INST))
from repo_paths import REPO_WF, COMFY_WF  # noqa: E402

REPO = REPO_WF / "人像写实化"
COMFY = COMFY_WF / "人像写实化"

POS_FLUX_PASS1 = (
    "RAW photograph, photorealistic, live-action, NOT anime, NOT cartoon, NOT illustration, NOT CGI, NOT 3D render.\n"
    "Keep the exact same person identity from the reference: same face geometry, same hairstyle, same individual, no face swap.\n"
    "Documentary portrait: natural skin texture with subtle pores and fine lines, realistic subsurface scattering, "
    "slight uneven skin tone, tiny imperfections allowed, thin natural lips, realistic eye catchlights, individual hair strands.\n"
    "Soft natural makeup only, no plastic doll skin, no beauty-filter airbrush.\n"
    "85mm portrait lens, f/2.8, shallow depth of field, natural color grading, subtle 35mm film grain, soft key light + ambient fill.\n"
    "Mainland Chinese woman portrait, candid restrained expression, neutral background bokeh."
)

POS_FLUX_PASS2 = (
    "RAW photograph, same person identity unchanged.\n"
    "Refine only: more photoreal skin micro-texture, natural pores, realistic specular highlights on skin, "
    "less synthetic smoothness, less waxy shine, documentary color, subtle film grain.\n"
    "NOT anime, NOT illustration, NOT plastic skin, NOT doll face."
)

NEG_FLUX = (
    "anime, manga, cartoon, doll, Barbie, plastic skin, wax figure, airbrushed, over-smooth, beauty filter, "
    "3d render, cgi, game character, illustration, painting, vector art, "
    "huge anime eyes, thick glossy lips, poreless skin, synthetic skin, uncanny valley, "
    "identity change, different person, face swap, deformed face, bad anatomy, "
    "oversaturated, HDR halos, watermark, text, logo, low quality, blurry, jpeg artifacts"
)

POS_SDXL = (
    "RAW photo, masterpiece, best quality, photorealistic, realistic portrait, "
    "mainland chinese woman, natural skin texture, subtle pores, thin natural lips, "
    "soft natural makeup, 85mm lens, shallow depth of field, film grain, natural lighting, "
    "same person as reference, keep face identity"
)

NEG_SDXL = (
    "anime, cartoon, manga, 3d, cgi, doll, plastic skin, airbrushed, poreless, waxy, "
    "identity change, different person, deformed, ugly, low quality, watermark, text"
)

README = """# 人像写实化流程（更像真人）

把「偏 AI / 偏动漫 / 塑料皮」的人像，改成 **RAW 照片感、真人皮肤质感**，同时尽量 **保住同一人**。

## 推荐顺序（8GB 笔记本）

| 步骤 | 工作流 | 说明 |
|------|--------|------|
| ① | `01_FLUX_人像写实化_I2I.json` | **主流程**：FLUX 图生图，去动漫感、加皮肤纹理 |
| ② | `02_FLUX_人像写实化_二遍微调.json` | **可选**：把 ① 输出再喂进去，denoise 更低，只修肤质 |
| ③ | `../后处理_脸部局部亮度.json` | **可选**：蒙版局部提亮/压暗，无模型 |
| 备 | `03_SDXL_人像写实化_I2I.json` | 已装 **AWPortrait XL** 时可试；与 FLUX 二选一或对比 |

每一步 **单独 Queue**，不要在一个图里同时跑两个大采样器。

## 启动 ComfyUI

```text
python main.py --lowvram
```

FLUX fp8 在 8GB 上较慢属正常；SDXL 一遍通常更快。

## 素材

- 输入：`ComfyUI/input/portrait_ai.png`（或任意偏假脸图）
- ① 输出：`output/sample/flux_photoreal_pass1/`
- ② 输入：把 pass1 最好的一张复制为 `portrait_pass1.png` 再跑 ②
- ② 输出：`output/sample/flux_photoreal_pass2/`

## 关键参数

### ① FLUX 主流程

| 参数 | 建议 | 说明 |
|------|------|------|
| **denoise** | `0.40`–`0.48` | 越大越不像原人；动漫感重可试 `0.48` |
| **FluxGuidance** | `3.5`–`4.0` | 过高易僵；写实词已写满 |
| **steps** | `26`–`30` | |
| **cfg** | `1.0` | FLUX 固定 |

### ② FLUX 二遍

| 参数 | 建议 |
|------|------|
| **denoise** | `0.24`–`0.32` |
| 换脸明显 | 降到 `0.22` 或跳过 ② |

### ③ SDXL（AWPortrait）

| 参数 | 建议 |
|------|------|
| **denoise** | `0.42`–`0.52` |
| **cfg** | `4`–`6` |
| 模型 | `AWPortrait_XL_ver1.1.safetensors` |

## 提示词原则（本仓库 FLUX 用英文）

- 正向强调：`RAW photograph`, `natural skin texture`, `subtle pores`, `NOT anime`, `same person identity`
- 负向强调：`plastic skin`, `doll`, `poreless`, `beauty filter`, `identity change`
- **不要用**「日系」「动漫」类词，否则易拉回二次元脸（见仓库惊悚场景说明）

## 何时用哪条

| 原图问题 | 建议 |
|----------|------|
| 明显动漫 / 插画脸 | ① denoise `0.45`–`0.50` |
| 已较真人，略塑料 | ① `0.38`–`0.42`，再 ② |
| 只有 SDXL、无 FLUX | 直接 ③ SDXL |
| 脸太暗 / 高光不对 | `后处理_脸部局部亮度.json` |

## 下游

写实人像 → `Flux_I2I_定妆照参考.json` / `日系惊悚_人物场景融合/` / `wan视频流` 关键帧。

## 重建本目录 json

```powershell
python c:\\tiger\\videoModel\\jinFrameComfyUI\\install\\build_photoreal_portrait_workflows.py
```
"""


def _flux_i2i(
    *,
    wf_id: str,
    filename: str,
    group_title: str,
    positive: str,
    denoise: float,
    guidance: float,
    save_prefix: str,
    load_title: str,
    sampler_title: str,
) -> dict:
    return {
        "id": wf_id,
        "revision": 0,
        "last_node_id": 12,
        "last_link_id": 15,
        "nodes": [
            {
                "id": 1,
                "type": "UNETLoader",
                "pos": [-780, 80],
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
                "pos": [-780, 240],
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
                "pos": [-780, 440],
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
                "id": 4,
                "type": "CLIPTextEncode",
                "pos": [-400, 80],
                "size": [440, 260],
                "flags": {},
                "order": 5,
                "mode": 0,
                "inputs": [
                    {"name": "clip", "type": "CLIP", "link": 2},
                    {"name": "text", "type": "STRING", "widget": {"name": "text"}, "link": None},
                ],
                "outputs": [{"name": "CONDITIONING", "type": "CONDITIONING", "links": [15]}],
                "properties": {"Node name for S&R": "CLIPTextEncode"},
                "title": "正向 · 写实 RAW",
                "widgets_values": [positive],
            },
            {
                "id": 12,
                "type": "FluxGuidance",
                "pos": [-400, 360],
                "size": [270, 58],
                "flags": {},
                "order": 6,
                "mode": 0,
                "inputs": [
                    {"name": "conditioning", "type": "CONDITIONING", "link": 15},
                    {"name": "guidance", "type": "FLOAT", "widget": {"name": "guidance"}, "link": None},
                ],
                "outputs": [{"name": "CONDITIONING", "type": "CONDITIONING", "links": [3]}],
                "properties": {"Node name for S&R": "FluxGuidance"},
                "widgets_values": [guidance],
            },
            {
                "id": 5,
                "type": "CLIPTextEncode",
                "pos": [-400, 440],
                "size": [420, 160],
                "flags": {},
                "order": 7,
                "mode": 0,
                "inputs": [
                    {"name": "clip", "type": "CLIP", "link": 14},
                    {"name": "text", "type": "STRING", "widget": {"name": "text"}, "link": None},
                ],
                "outputs": [{"name": "CONDITIONING", "type": "CONDITIONING", "links": [5]}],
                "properties": {"Node name for S&R": "CLIPTextEncode"},
                "title": "负向 · 反动漫/塑料皮",
                "widgets_values": [NEG_FLUX],
            },
            {
                "id": 10,
                "type": "LoadImage",
                "pos": [-780, 600],
                "size": [320, 340],
                "flags": {},
                "order": 0,
                "mode": 0,
                "inputs": [
                    {"name": "image", "type": "COMBO", "widget": {"name": "image"}, "link": None},
                    {"name": "upload", "type": "IMAGEUPLOAD", "widget": {"name": "upload"}, "link": None},
                ],
                "outputs": [
                    {"name": "IMAGE", "type": "IMAGE", "links": [12]},
                    {"name": "MASK", "type": "MASK", "links": None},
                ],
                "properties": {"Node name for S&R": "LoadImage"},
                "title": load_title,
                "widgets_values": ["portrait_ai.png", "image"],
            },
            {
                "id": 11,
                "type": "VAEEncode",
                "pos": [-400, 600],
                "size": [210, 46],
                "flags": {},
                "order": 4,
                "mode": 0,
                "inputs": [
                    {"name": "pixels", "type": "IMAGE", "link": 12},
                    {"name": "vae", "type": "VAE", "link": 10},
                ],
                "outputs": [{"name": "LATENT", "type": "LATENT", "links": [6]}],
                "properties": {"Node name for S&R": "VAEEncode"},
                "widgets_values": [],
            },
            {
                "id": 7,
                "type": "KSampler",
                "pos": [80, 200],
                "size": [315, 474],
                "flags": {},
                "order": 8,
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
                "title": sampler_title,
                "widgets_values": [0, "randomize", 28, 1.0, "euler", "simple", denoise],
            },
            {
                "id": 8,
                "type": "VAEDecode",
                "pos": [450, 200],
                "size": [270, 82],
                "flags": {},
                "order": 9,
                "mode": 0,
                "inputs": [
                    {"name": "samples", "type": "LATENT", "link": 7},
                    {"name": "vae", "type": "VAE", "link": 11},
                ],
                "outputs": [{"name": "IMAGE", "type": "IMAGE", "links": [8, 13]}],
                "properties": {"Node name for S&R": "VAEDecode"},
                "widgets_values": [],
            },
            {
                "id": 9,
                "type": "SaveImage",
                "pos": [750, 200],
                "size": [270, 82],
                "flags": {},
                "order": 10,
                "mode": 0,
                "inputs": [
                    {"name": "images", "type": "IMAGE", "link": 8},
                    {"name": "filename_prefix", "type": "STRING", "widget": {"name": "filename_prefix"}, "link": None},
                ],
                "outputs": [],
                "properties": {"Node name for S&R": "SaveImage"},
                "widgets_values": [save_prefix],
            },
            {
                "id": 13,
                "type": "PreviewImage",
                "pos": [750, 320],
                "size": [280, 280],
                "flags": {},
                "order": 11,
                "mode": 0,
                "inputs": [{"name": "images", "type": "IMAGE", "link": 13}],
                "outputs": [],
                "properties": {"Node name for S&R": "PreviewImage"},
                "title": "预览",
            },
        ],
        "links": [
            [1, 1, 0, 7, 0, "MODEL"],
            [2, 2, 0, 4, 0, "CLIP"],
            [3, 12, 0, 7, 1, "CONDITIONING"],
            [14, 2, 0, 5, 0, "CLIP"],
            [15, 4, 0, 12, 0, "CONDITIONING"],
            [5, 5, 0, 7, 2, "CONDITIONING"],
            [6, 11, 0, 7, 3, "LATENT"],
            [7, 7, 0, 8, 0, "LATENT"],
            [8, 8, 0, 9, 0, "IMAGE"],
            [10, 3, 0, 11, 1, "VAE"],
            [11, 3, 0, 8, 1, "VAE"],
            [12, 10, 0, 11, 0, "IMAGE"],
            [13, 8, 0, 13, 0, "IMAGE"],
        ],
        "groups": [
            {
                "id": 1,
                "title": group_title,
                "bounding": [-820, 30, 1280, 980],
                "color": "#48a",
                "font_size": 22,
                "flags": {},
            }
        ],
        "config": {},
        "extra": {"ds": {"scale": 1.0, "offset": [900, 200]}},
        "version": 0.4,
    }


def _sdxl_i2i() -> dict:
    return {
        "id": "sdxl-photoreal-i2i",
        "revision": 0,
        "last_node_id": 10,
        "last_link_id": 14,
        "nodes": [
            {
                "id": 1,
                "type": "CheckpointLoaderSimple",
                "pos": [-820, 80],
                "size": [340, 98],
                "flags": {},
                "order": 1,
                "mode": 0,
                "inputs": [{"name": "ckpt_name", "type": "COMBO", "widget": {"name": "ckpt_name"}, "link": None}],
                "outputs": [
                    {"name": "MODEL", "type": "MODEL", "links": [1]},
                    {"name": "CLIP", "type": "CLIP", "links": [2, 3]},
                    {"name": "VAE", "type": "VAE", "links": [10, 11]},
                ],
                "properties": {"Node name for S&R": "CheckpointLoaderSimple"},
                "title": "AWPortrait XL（东亚写实人像）",
                "widgets_values": ["AWPortrait_XL_ver1.1.safetensors"],
            },
            {
                "id": 2,
                "type": "CLIPTextEncode",
                "pos": [-400, 40],
                "size": [420, 200],
                "flags": {},
                "order": 4,
                "mode": 0,
                "inputs": [
                    {"name": "clip", "type": "CLIP", "link": 2},
                    {"name": "text", "type": "STRING", "widget": {"name": "text"}, "link": None},
                ],
                "outputs": [{"name": "CONDITIONING", "type": "CONDITIONING", "links": [4]}],
                "properties": {"Node name for S&R": "CLIPTextEncode"},
                "title": "正向",
                "widgets_values": [POS_SDXL],
            },
            {
                "id": 3,
                "type": "CLIPTextEncode",
                "pos": [-400, 280],
                "size": [420, 140],
                "flags": {},
                "order": 5,
                "mode": 0,
                "inputs": [
                    {"name": "clip", "type": "CLIP", "link": 3},
                    {"name": "text", "type": "STRING", "widget": {"name": "text"}, "link": None},
                ],
                "outputs": [{"name": "CONDITIONING", "type": "CONDITIONING", "links": [5]}],
                "properties": {"Node name for S&R": "CLIPTextEncode"},
                "title": "负向",
                "widgets_values": [NEG_SDXL],
            },
            {
                "id": 8,
                "type": "LoadImage",
                "pos": [-820, 280],
                "size": [320, 314],
                "flags": {},
                "order": 0,
                "mode": 0,
                "inputs": [
                    {"name": "image", "type": "COMBO", "widget": {"name": "image"}, "link": None},
                    {"name": "upload", "type": "IMAGEUPLOAD", "widget": {"name": "upload"}, "link": None},
                ],
                "outputs": [{"name": "IMAGE", "type": "IMAGE", "links": [12]}],
                "properties": {"Node name for S&R": "LoadImage"},
                "title": "上传偏 AI 的人像",
                "widgets_values": ["portrait_ai.png", "image"],
            },
            {
                "id": 9,
                "type": "VAEEncode",
                "pos": [-400, 480],
                "size": [210, 46],
                "flags": {},
                "order": 3,
                "mode": 0,
                "inputs": [
                    {"name": "pixels", "type": "IMAGE", "link": 12},
                    {"name": "vae", "type": "VAE", "link": 10},
                ],
                "outputs": [{"name": "LATENT", "type": "LATENT", "links": [6]}],
                "properties": {"Node name for S&R": "VAEEncode"},
                "widgets_values": [],
            },
            {
                "id": 5,
                "type": "KSampler",
                "pos": [80, 120],
                "size": [315, 474],
                "flags": {},
                "order": 6,
                "mode": 0,
                "inputs": [
                    {"name": "model", "type": "MODEL", "link": 1},
                    {"name": "positive", "type": "CONDITIONING", "link": 4},
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
                "title": "denoise 0.42~0.50 保脸",
                "widgets_values": [0, "randomize", 28, 5.0, "dpmpp_2m", "karras", 0.46],
            },
            {
                "id": 6,
                "type": "VAEDecode",
                "pos": [450, 160],
                "size": [210, 46],
                "flags": {},
                "order": 7,
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
                "id": 7,
                "type": "SaveImage",
                "pos": [720, 160],
                "size": [270, 58],
                "flags": {},
                "order": 8,
                "mode": 0,
                "inputs": [
                    {"name": "images", "type": "IMAGE", "link": 8},
                    {"name": "filename_prefix", "type": "STRING", "widget": {"name": "filename_prefix"}, "link": None},
                ],
                "outputs": [],
                "properties": {"Node name for S&R": "SaveImage"},
                "widgets_values": ["sample/sdxl_photoreal_i2i"],
            },
        ],
        "links": [
            [1, 1, 0, 5, 0, "MODEL"],
            [2, 1, 1, 2, 0, "CLIP"],
            [3, 1, 1, 3, 0, "CLIP"],
            [4, 2, 0, 5, 1, "CONDITIONING"],
            [5, 3, 0, 5, 2, "CONDITIONING"],
            [6, 9, 0, 5, 3, "LATENT"],
            [7, 5, 0, 6, 0, "LATENT"],
            [8, 6, 0, 7, 0, "IMAGE"],
            [10, 1, 2, 9, 1, "VAE"],
            [11, 1, 2, 6, 1, "VAE"],
            [12, 8, 0, 9, 0, "IMAGE"],
        ],
        "groups": [
            {
                "id": 1,
                "title": "SDXL AWPortrait · 人像写实化 I2I（备选）",
                "bounding": [-860, 20, 1100, 720],
                "color": "#a58",
                "font_size": 22,
                "flags": {},
            }
        ],
        "config": {},
        "extra": {"ds": {"scale": 1.0, "offset": [900, 200]}},
        "version": 0.4,
    }


def main() -> None:
    REPO.mkdir(parents=True, exist_ok=True)
    files = {
        "01_FLUX_人像写实化_I2I.json": _flux_i2i(
            wf_id="flux-photoreal-pass1",
            filename="01",
            group_title="① FLUX 人像写实化 · 主流程（单独 Queue）",
            positive=POS_FLUX_PASS1,
            denoise=0.44,
            guidance=3.6,
            save_prefix="sample/flux_photoreal_pass1",
            load_title="上传：偏 AI / 动漫感人像",
            sampler_title="denoise 0.40~0.48 去动漫 | 过高易换脸",
        ),
        "02_FLUX_人像写实化_二遍微调.json": _flux_i2i(
            wf_id="flux-photoreal-pass2",
            filename="02",
            group_title="② FLUX 二遍微调 · 只修肤质（输入=①输出）",
            positive=POS_FLUX_PASS2,
            denoise=0.28,
            guidance=3.4,
            save_prefix="sample/flux_photoreal_pass2",
            load_title="上传：① 输出的 portrait_pass1.png",
            sampler_title="denoise 0.22~0.32 保身份",
        ),
        "03_SDXL_人像写实化_I2I.json": _sdxl_i2i(),
    }
    for name, data in files.items():
        path = REPO / name
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(path.as_posix().encode("unicode_escape").decode())
    (REPO / "README.md").write_text(README, encoding="utf-8")
    print("README.md OK")

    if COMFY.parent.exists():
        COMFY.mkdir(parents=True, exist_ok=True)
        for name in list(files) + ["README.md"]:
            shutil.copy2(REPO / name, COMFY / name)
        print("synced ComfyUI workflows OK")


if __name__ == "__main__":
    main()
