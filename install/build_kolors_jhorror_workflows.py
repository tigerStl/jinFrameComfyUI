"""Build Kolors T2I horror scene + compose workflows (mirrors 日系惊悚_场景 / Hunyuan compose)."""
import importlib.util
import json
import shutil
import sys
import uuid
from pathlib import Path

_INST = Path(__file__).resolve().parent
sys.path.insert(0, str(_INST))
from repo_paths import REPO_ROOT, REPO_WF, COMFY_WF  # noqa: E402

REPO = REPO_ROOT
OUT = REPO_WF / "Kolors_日系惊悚"
COMFY = COMFY_WF / "Kolors_日系惊悚"

_SPEC = importlib.util.spec_from_file_location(
    "jhorror_scenes",
    REPO / "install" / "build_jhorror_scene_workflows.py",
)
_jh = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_jh)
SCENES = _jh.SCENES

KOLORS_POS_WRAP = (
    "高清摄影，电影静帧，日系心理惊悚空镜，低饱和冷色调，惨绿荧光灯与深阴影，"
    "非血腥，画面无人，非动漫插画。\n{scene}\n无文字水印，写实细节。"
)
KOLORS_NEG = (
    "丑陋，变形，低质量，模糊，水印，乱码，动漫，插画，卡通，二次元，血腥，"
    "尸体，过饱和，暖黄灯光，明亮大堂，欢快，人群"
)

COMPOSE_T2I = (
    "【主体】一位27岁中国大陆汉族女性，鹅蛋脸，薄唇，黑色中长发，白衬衫灰色铅笔裙，\n"
    "【环境】老旧居民楼楼梯间，斑驳墙面，冷色荧光灯，\n"
    "【光影】低饱和，轻微雾气，\n"
    "【构图】中景，浅景深，悬疑氛围，高清摄影"
)
COMPOSE_I2I = (
    "保持参考图中人物身份、脸型与姿势不变。\n"
    "【合成目标】仅替换背景为惊悚场景，冷色惨绿荧光，低饱和。\n"
    "【氛围】悬疑电影感，高清摄影，非动漫。"
)


def _kolors_pipeline(
    *,
    title: str,
    positive: str,
    width: int,
    height: int,
    prefix: str,
    note: str,
    chatglm_mode: str = "load",
    glm_file: str = "chatglm3-4bit.safetensors",
    glm_precision: str = "quant4",
) -> dict:
    """chatglm_mode: load | download"""
    nodes = [
        {
            "id": 1,
            "type": "DownloadAndLoadKolorsModel",
            "pos": [-400, 200],
            "size": [320, 82],
            "flags": {},
            "order": 1,
            "mode": 0,
            "inputs": [
                {"name": "model", "type": "COMBO", "widget": {"name": "model"}, "link": None},
                {"name": "precision", "type": "COMBO", "widget": {"name": "precision"}, "link": None},
            ],
            "outputs": [{"name": "kolors_model", "type": "KOLORSMODEL", "links": [1]}],
            "properties": {"Node name for S&R": "DownloadAndLoadKolorsModel"},
            "widgets_values": ["Kwai-Kolors/Kolors", "fp16"],
        },
        {
            "id": 11,
            "type": "VAELoader",
            "pos": [900, 200],
            "size": [270, 58],
            "flags": {},
            "order": 0,
            "mode": 0,
            "inputs": [{"name": "vae_name", "type": "COMBO", "widget": {"name": "vae_name"}, "link": None}],
            "outputs": [{"name": "VAE", "type": "VAE", "links": [12]}],
            "properties": {"Node name for S&R": "VAELoader"},
            "widgets_values": ["sdxl.vae.safetensors"],
        },
        {
            "id": 10,
            "type": "VAEDecode",
            "pos": [900, 320],
            "size": [210, 46],
            "flags": {},
            "order": 6,
            "mode": 0,
            "inputs": [
                {"name": "samples", "type": "LATENT", "link": 18},
                {"name": "vae", "type": "VAE", "link": 12},
            ],
            "outputs": [{"name": "IMAGE", "type": "IMAGE", "links": [13]}],
            "properties": {"Node name for S&R": "VAEDecode"},
            "widgets_values": [],
        },
        {
            "id": 9,
            "type": "SaveImage",
            "pos": [1150, 320],
            "size": [280, 58],
            "flags": {},
            "order": 7,
            "mode": 0,
            "inputs": [
                {"name": "images", "type": "IMAGE", "link": 13},
                {"name": "filename_prefix", "type": "STRING", "widget": {"name": "filename_prefix"}, "link": None},
            ],
            "outputs": [],
            "properties": {"Node name for S&R": "SaveImage"},
            "widgets_values": [prefix],
        },
        {
            "id": 12,
            "type": "KolorsTextEncode",
            "pos": [-80, 380],
            "size": [460, 200],
            "flags": {},
            "order": 4,
            "mode": 0,
            "inputs": [
                {"name": "chatglm3_model", "type": "CHATGLM3MODEL", "link": 14},
                {"name": "prompt", "type": "STRING", "widget": {"name": "prompt"}, "link": None},
                {"name": "negative_prompt", "type": "STRING", "widget": {"name": "negative_prompt"}, "link": None},
                {"name": "num_images_per_prompt", "type": "INT", "widget": {"name": "num_images_per_prompt"}, "link": None},
            ],
            "outputs": [{"name": "kolors_embeds", "type": "KOLORS_EMBEDS", "links": [17]}],
            "properties": {"Node name for S&R": "KolorsTextEncode"},
            "title": "正向 · 中文",
            "widgets_values": [positive, KOLORS_NEG, 1],
        },
        {
            "id": 14,
            "type": "KolorsSampler",
            "pos": [480, 360],
            "size": [315, 222],
            "flags": {},
            "order": 5,
            "mode": 0,
            "inputs": [
                {"name": "kolors_model", "type": "KOLORSMODEL", "link": 16},
                {"name": "kolors_embeds", "type": "KOLORS_EMBEDS", "link": 17},
                {"name": "width", "type": "INT", "widget": {"name": "width"}, "link": None},
                {"name": "height", "type": "INT", "widget": {"name": "height"}, "link": None},
                {"name": "seed", "type": "INT", "widget": {"name": "seed"}, "link": None},
                {"name": "steps", "type": "INT", "widget": {"name": "steps"}, "link": None},
                {"name": "cfg", "type": "FLOAT", "widget": {"name": "cfg"}, "link": None},
                {"name": "scheduler", "type": "COMBO", "widget": {"name": "scheduler"}, "link": None},
            ],
            "outputs": [{"name": "latent", "type": "LATENT", "links": [18]}],
            "properties": {"Node name for S&R": "KolorsSampler"},
            "title": "Kolors Sampler",
            "widgets_values": [width, height, 0, "randomize", 25, 5.0, "EulerDiscreteScheduler"],
        },
        {
            "id": 99,
            "type": "MarkdownNote",
            "pos": [-400, -120],
            "size": [520, 280],
            "flags": {},
            "order": 0,
            "mode": 0,
            "inputs": [],
            "outputs": [],
            "title": "说明",
            "properties": {},
            "widgets_values": [note],
            "color": "#432",
            "bgcolor": "#1a1a1a",
        },
    ]

    if chatglm_mode == "load":
        nodes.insert(
            1,
            {
                "id": 13,
                "type": "LoadChatGLM3",
                "pos": [-400, 360],
                "size": [320, 58],
                "flags": {},
                "order": 2,
                "mode": 0,
                "inputs": [
                    {
                        "name": "chatglm3_checkpoint",
                        "type": "COMBO",
                        "widget": {"name": "chatglm3_checkpoint"},
                        "link": None,
                    }
                ],
                "outputs": [{"name": "chatglm3_model", "type": "CHATGLM3MODEL", "links": [14]}],
                "properties": {"Node name for S&R": "LoadChatGLM3"},
                "title": "ChatGLM3 · 8GB 用 quant4",
                "widgets_values": [glm_file],
            },
        )
    else:
        nodes.insert(
            1,
            {
                "id": 13,
                "type": "DownloadAndLoadChatGLM3",
                "pos": [-400, 360],
                "size": [320, 58],
                "flags": {},
                "order": 2,
                "mode": 0,
                "inputs": [
                    {"name": "precision", "type": "COMBO", "widget": {"name": "precision"}, "link": None}
                ],
                "outputs": [{"name": "chatglm3_model", "type": "CHATGLM3MODEL", "links": [14]}],
                "properties": {"Node name for S&R": "DownloadAndLoadChatGLM3"},
                "widgets_values": [glm_precision],
            },
        )

    links = [
        [1, 1, 0, 14, 0, "KOLORSMODEL"],
        [14, 13, 0, 12, 0, "CHATGLM3MODEL"],
        [16, 1, 0, 14, 0, "KOLORSMODEL"],
        [17, 12, 0, 14, 1, "KOLORS_EMBEDS"],
        [18, 14, 0, 10, 0, "LATENT"],
        [12, 11, 0, 10, 1, "VAE"],
        [13, 10, 0, 9, 0, "IMAGE"],
    ]
    return {
        "id": str(uuid.uuid4()),
        "revision": 0,
        "last_node_id": 99,
        "last_link_id": 18,
        "nodes": nodes,
        "links": links,
        "groups": [
            {
                "id": 1,
                "title": title,
                "bounding": [-420, -140, 1480, 720],
                "color": "#5a3",
                "font_size": 22,
                "flags": {},
            }
        ],
        "config": {},
        "extra": {"ds": {"scale": 0.85, "offset": [500, 200]}},
        "version": 0.4,
    }


def _kolors_i2i_compose() -> dict:
    w = _kolors_pipeline(
        title="Kolors · 图形合成 ② 图生图",
        positive=COMPOSE_I2I,
        width=768,
        height=1024,
        prefix="sample/kolors_compose_02_i2i",
        note=(
            "## ② 仅图生图\nLoadImage → VAEEncode → KolorsSampler（denoise=0.55）\n"
            "单独 Queue，勿与 01 文生图同画布一次跑。\n"
            "两图融合更快：Flux_人物场景融合_单人。"
        ),
    )
    # Add LoadImage + VAEEncode + denoise on sampler
    w["nodes"].append(
        {
            "id": 20,
            "type": "LoadImage",
            "pos": [-400, 520],
            "size": [320, 314],
            "flags": {},
            "order": 0,
            "mode": 0,
            "inputs": [
                {"name": "image", "type": "COMBO", "widget": {"name": "image"}, "link": None},
                {"name": "upload", "type": "IMAGEUPLOAD", "widget": {"name": "upload"}, "link": None},
            ],
            "outputs": [
                {"name": "IMAGE", "type": "IMAGE", "links": [30]},
                {"name": "MASK", "type": "MASK", "links": None},
            ],
            "properties": {"Node name for S&R": "LoadImage"},
            "title": "reference.png",
            "widgets_values": ["reference.png", "image"],
        }
    )
    w["nodes"].append(
        {
            "id": 21,
            "type": "VAEEncode",
            "pos": [-80, 620],
            "size": [210, 46],
            "flags": {},
            "order": 3,
            "mode": 0,
            "inputs": [
                {"name": "pixels", "type": "IMAGE", "link": 30},
                {"name": "vae", "type": "VAE", "link": 31},
            ],
            "outputs": [{"name": "LATENT", "type": "LATENT", "links": [32]}],
            "properties": {"Node name for S&R": "VAEEncode"},
            "widgets_values": [],
        }
    )
    for n in w["nodes"]:
        if n["id"] == 11:
            n["outputs"][0]["links"] = [12, 31]
        if n["id"] == 14:
            n["inputs"] = [
                {"name": "kolors_model", "type": "KOLORSMODEL", "link": 16},
                {"name": "kolors_embeds", "type": "KOLORS_EMBEDS", "link": 17},
                {"name": "latent", "type": "LATENT", "link": 32},
                {"name": "width", "type": "INT", "widget": {"name": "width"}, "link": None},
                {"name": "height", "type": "INT", "widget": {"name": "height"}, "link": None},
                {"name": "seed", "type": "INT", "widget": {"name": "seed"}, "link": None},
                {"name": "steps", "type": "INT", "widget": {"name": "steps"}, "link": None},
                {"name": "cfg", "type": "FLOAT", "widget": {"name": "cfg"}, "link": None},
                {"name": "scheduler", "type": "COMBO", "widget": {"name": "scheduler"}, "link": None},
                {
                    "name": "denoise_strength",
                    "type": "FLOAT",
                    "widget": {"name": "denoise_strength"},
                    "link": None,
                },
            ]
            n["widgets_values"] = [768, 1024, 0, "randomize", 25, 5.0, "EulerDiscreteScheduler", 0.55]
    w["links"].extend(
        [
            [30, 20, 0, 21, 0, "IMAGE"],
            [31, 11, 0, 21, 1, "VAE"],
            [32, 21, 0, 14, 2, "LATENT"],
        ]
    )
    w["last_link_id"] = 32
    return w


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    note_base = (
        "## Kolors 惊悚场景\n"
        "- 节点：`DownloadAndLoadKolorsModel` + `LoadChatGLM3`（quant4）\n"
        "- VAE：`sdxl.vae.safetensors`（与 SDXL 共用）\n"
        "- 安装：`install/install_kolors.ps1`\n"
        "- 8GB：`--lowvram`，首次会下载 `models/diffusers/Kolors`\n"
    )

    tpl = _kolors_pipeline(
        title="Kolors · 模板",
        positive=KOLORS_POS_WRAP.format(scene="【在此写场景】"),
        width=1024,
        height=768,
        prefix="sample/kolors_jhorror_scene",
        note=note_base,
    )
    (OUT / "Kolors_T2I_惊悚_场景.json").write_text(
        json.dumps(tpl, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    for sc in SCENES:
        w, h = (1024, 768) if sc["landscape"] else (768, 1024)
        pos = KOLORS_POS_WRAP.format(scene=sc["hunyuan_scene"])
        data = _kolors_pipeline(
            title=f"Kolors · 日系惊悚 · {sc['slug']}",
            positive=pos,
            width=w,
            height=h,
            prefix=f"sample/kolors_jhorror_{sc['slug']}",
            note=note_base + f"\n场景：**{sc['slug']}**",
        )
        fname = f"Kolors_T2I_惊悚_{sc['slug']}.json"
        (OUT / fname).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    t2i = _kolors_pipeline(
        title="Kolors · 图形合成 ① 文生图",
        positive=COMPOSE_T2I,
        width=768,
        height=1024,
        prefix="sample/kolors_compose_01_t2i",
        note="## ① 仅文生图\n分层写【主体】【环境】【光影】【构图】。单独 Queue。",
    )
    (OUT / "Kolors_图形合成_01_文生图.json").write_text(
        json.dumps(t2i, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "Kolors_图形合成_02_图生图.json").write_text(
        json.dumps(_kolors_i2i_compose(), ensure_ascii=False, indent=2), encoding="utf-8"
    )

    readme = OUT / "README.md"
    readme.write_text(
        """# Kolors · 日系惊悚作图

快手 Kolors + [ComfyUI-KwaiKolorsWrapper](https://github.com/kijai/ComfyUI-KwaiKolorsWrapper)。

## 安装

```powershell
c:\\tiger\\videoModel\\jinFrameComfyUI\\install\\install_kolors.ps1
```

- 自定义节点 → `ComfyUI/custom_nodes/ComfyUI-KwaiKolorsWrapper`
- ChatGLM3 quant4 → `models/LLM/checkpoints/chatglm3-4bit.safetensors`
- Kolors UNet → 首次 Queue 自动下载到 `models/diffusers/Kolors`

## 工作流

| 类型 | 文件 |
|------|------|
| 惊悚空镜（与 SDXL/Flux/Hunyuan 同场景表） | `Kolors_T2I_惊悚_*.json` |
| 图形合成 文生图 | `Kolors_图形合成_01_文生图.json` |
| 图形合成 图生图 | `Kolors_图形合成_02_图生图.json` |

## 8GB 要点

- `Load ChatGLM3` 选 **chatglm3-4bit.safetensors**（勿用 fp16）
- 启动：`--lowvram`
- 横构图 1024×768，竖 768×1024

## 重建

```powershell
python install/build_kolors_jhorror_workflows.py
```

## 对照

| 模型 | 目录 |
|------|------|
| FLUX / SDXL / HunyuanDiT | `日系惊悚_场景/` |
| Kolors | 本目录 `Kolors_日系惊悚/` |
| FLUX 人景两图融合 | `日系惊悚_人物场景融合/` |
""",
        encoding="utf-8",
    )

    if COMFY.parent.exists():
        COMFY.mkdir(parents=True, exist_ok=True)
        for p in OUT.glob("*.json"):
            shutil.copy(p, COMFY / p.name)
        shutil.copy(readme, COMFY / "README.md")
    print("ok", len(list(OUT.glob("Kolors_T2I*.json"))), "scene workflows")


if __name__ == "__main__":
    main()
