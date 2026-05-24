"""Split HunyuanDiT_图形合成 into 01 T2I and 02 I2I workflows."""
import json
import shutil
import sys
from pathlib import Path

_INST = Path(__file__).resolve().parent
sys.path.insert(0, str(_INST))
from repo_paths import REPO_WF, COMFY_WF  # noqa: E402

REPO = REPO_WF
COMFY = COMFY_WF
CKPT = "hunyuan_dit_comfyui/hunyuan_dit_1.2.safetensors"

T2I_POS = (
    "高清摄影，电影静帧，日系心理惊悚空镜，低饱和冷色荧光灯，非血腥，\n"
    "【主体】一位27岁中国大陆汉族女性，鹅蛋脸，薄唇，黑色中长发，白衬衫与灰色铅笔裙，\n"
    "【环境】中国大陆老旧居民楼楼梯间，斑驳墙面，金属扶手，\n"
    "【光影】冷色荧光灯，低饱和度，轻微雾气，\n"
    "【构图】中景，浅景深，人物偏左，右侧留白，悬疑氛围"
)
I2I_POS = (
    "保持参考图中人物身份、脸型与姿势不变。\n"
    "【合成目标】仅替换背景为惊悚场景（走廊/办公大堂等），冷色荧光灯，低饱和度。\n"
    "【氛围】悬疑电影感，高清摄影，非动漫。"
)
NEG = (
    "丑陋，变形，低质量，模糊，水印，乱码文字，日系动漫脸，厚唇，高颧骨，"
    "多余手指，肢体错误，裸露，色情，血腥"
)


def t2i_workflow() -> dict:
    return {
        "id": "hunyuan-compose-t2i",
        "revision": 0,
        "last_node_id": 7,
        "last_link_id": 10,
        "nodes": [
            _ckpt(1, [1, 2, 3], [10]),
            _pos(2, 2, 4, T2I_POS, "正向 · 文生图（中文分层）"),
            _neg(3, 3, 5),
            _empty(4, 6, 768, 1024, "竖构图 768x1024"),
            _sampler(5, 1, 4, 5, 6, 7, "文生图 · steps 28 denoise 1", 1.0, 7),
            _decode(6, 7, 10, 8),
            _save(7, 8, "sample/hunyuan_compose_01_t2i"),
            _note(
                99,
                "① 仅文生图\n\n用【主体】【环境】【光影】【构图】写中文。\n"
                "8GB：`--lowvram --cpu-vae`。约 5~12 分钟。\n"
                "人物+场景合成请用 `HunyuanDiT_图形合成_02_图生图` 或 FLUX 人物场景融合。",
                [-900, -200],
            ),
        ],
        "links": [
            [1, 1, 0, 5, 0, "MODEL"],
            [2, 1, 1, 2, 0, "CLIP"],
            [3, 1, 1, 3, 0, "CLIP"],
            [4, 2, 0, 5, 1, "CONDITIONING"],
            [5, 3, 0, 5, 2, "CONDITIONING"],
            [6, 4, 0, 5, 3, "LATENT"],
            [7, 5, 0, 6, 0, "LATENT"],
            [8, 6, 0, 7, 0, "IMAGE"],
            [10, 1, 2, 6, 1, "VAE"],
        ],
        "groups": [
            {
                "id": 1,
                "title": "Hunyuan DiT · 图形合成 ① 文生图（单独 Queue）",
                "bounding": [-920, -220, 1100, 720],
                "color": "#3a5",
                "font_size": 22,
                "flags": {},
            }
        ],
        "config": {},
        "extra": {"ds": {"scale": 0.9, "offset": [900, 200]}},
        "version": 0.4,
    }


def i2i_workflow() -> dict:
    return {
        "id": "hunyuan-compose-i2i",
        "revision": 0,
        "last_node_id": 8,
        "last_link_id": 11,
        "nodes": [
            _ckpt(1, [1, 2, 3], [10, 20]),
            _load(8, 16, "reference.png", "上传参考图（人物/草图）", [-900, 480]),
            _pos(2, 2, 4, I2I_POS, "正向 · 图生图合成"),
            _neg(3, 3, 5),
            _vae_enc(4, 16, 20, 6),
            _sampler(5, 1, 4, 5, 6, 7, "图生图 · steps 28 denoise 0.55", 0.55, 80),
            _decode(6, 7, 10, 8),
            _save(7, 8, "sample/hunyuan_compose_02_i2i"),
            _note(
                99,
                "② 仅图生图合成\n\n"
                "上传 reference.png → Queue **只此一条**。\n"
                "denoise 0.45~0.6：保脸换背景。\n"
                "8GB：`--lowvram --cpu-vae`。约 5~10 分钟。\n"
                "人物+场景两图融合更快：Flux_人物场景融合_单人。",
                [-900, 120],
            ),
        ],
        "links": [
            [1, 1, 0, 5, 0, "MODEL"],
            [2, 1, 1, 2, 0, "CLIP"],
            [3, 1, 1, 3, 0, "CLIP"],
            [4, 2, 0, 5, 1, "CONDITIONING"],
            [5, 3, 0, 5, 2, "CONDITIONING"],
            [6, 4, 0, 5, 3, "LATENT"],
            [7, 5, 0, 6, 0, "LATENT"],
            [8, 6, 0, 7, 0, "IMAGE"],
            [10, 1, 2, 6, 1, "VAE"],
            [16, 8, 0, 4, 0, "IMAGE"],
            [20, 1, 2, 4, 1, "VAE"],
        ],
        "groups": [
            {
                "id": 1,
                "title": "Hunyuan DiT · 图形合成 ② 图生图（单独 Queue）",
                "bounding": [-920, 80, 1100, 780],
                "color": "#58a",
                "font_size": 22,
                "flags": {},
            }
        ],
        "config": {},
        "extra": {"ds": {"scale": 0.9, "offset": [900, 280]}},
        "version": 0.4,
    }


def _ckpt(nid, clip_links, vae_links):
    return {
        "id": nid,
        "type": "CheckpointLoaderSimple",
        "pos": [-820, 200],
        "size": [320, 98],
        "flags": {},
        "order": 1,
        "mode": 0,
        "inputs": [{"name": "ckpt_name", "type": "COMBO", "widget": {"name": "ckpt_name"}, "link": None}],
        "outputs": [
            {"name": "MODEL", "type": "MODEL", "links": [clip_links[0]]},
            {"name": "CLIP", "type": "CLIP", "links": clip_links[1:]},
            {"name": "VAE", "type": "VAE", "links": vae_links},
        ],
        "properties": {"Node name for S&R": "CheckpointLoaderSimple"},
        "title": "Hunyuan DiT 1.2",
        "widgets_values": [CKPT],
    }


def _pos(nid, clip_in, cond_out, text, title):
    return {
        "id": nid,
        "type": "CLIPTextEncode",
        "pos": [-400, 80],
        "size": [440, 220],
        "flags": {},
        "order": 3,
        "mode": 0,
        "inputs": [
            {"name": "clip", "type": "CLIP", "link": clip_in},
            {"name": "text", "type": "STRING", "widget": {"name": "text"}, "link": None},
        ],
        "outputs": [{"name": "CONDITIONING", "type": "CONDITIONING", "links": [cond_out]}],
        "properties": {"Node name for S&R": "CLIPTextEncode"},
        "title": title,
        "widgets_values": [text],
    }


def _neg(nid, clip_in, cond_out):
    return {
        "id": nid,
        "type": "CLIPTextEncode",
        "pos": [-400, 320],
        "size": [440, 120],
        "flags": {},
        "order": 4,
        "mode": 0,
        "inputs": [
            {"name": "clip", "type": "CLIP", "link": clip_in},
            {"name": "text", "type": "STRING", "widget": {"name": "text"}, "link": None},
        ],
        "outputs": [{"name": "CONDITIONING", "type": "CONDITIONING", "links": [cond_out]}],
        "properties": {"Node name for S&R": "CLIPTextEncode"},
        "title": "负向",
        "widgets_values": [NEG],
    }


def _empty(nid, latent_out, w, h, title):
    return {
        "id": nid,
        "type": "EmptyLatentImage",
        "pos": [-400, 480],
        "size": [270, 110],
        "flags": {},
        "order": 2,
        "mode": 0,
        "inputs": [
            {"name": "width", "type": "INT", "widget": {"name": "width"}, "link": None},
            {"name": "height", "type": "INT", "widget": {"name": "height"}, "link": None},
            {"name": "batch_size", "type": "INT", "widget": {"name": "batch_size"}, "link": None},
        ],
        "outputs": [{"name": "LATENT", "type": "LATENT", "links": [latent_out]}],
        "properties": {"Node name for S&R": "EmptyLatentImage"},
        "title": title,
        "widgets_values": [w, h, 1],
    }


def _load(nid, img_out, fname, title, pos):
    return {
        "id": nid,
        "type": "LoadImage",
        "pos": pos,
        "size": [320, 314],
        "flags": {},
        "order": 0,
        "mode": 0,
        "inputs": [
            {"name": "image", "type": "COMBO", "widget": {"name": "image"}, "link": None},
            {"name": "upload", "type": "IMAGEUPLOAD", "widget": {"name": "upload"}, "link": None},
        ],
        "outputs": [
            {"name": "IMAGE", "type": "IMAGE", "links": [img_out]},
            {"name": "MASK", "type": "MASK", "links": None},
        ],
        "properties": {"Node name for S&R": "LoadImage"},
        "title": title,
        "widgets_values": [fname, "image"],
    }


def _vae_enc(nid, img_in, vae_in, latent_out):
    return {
        "id": nid,
        "type": "VAEEncode",
        "pos": [-400, 520],
        "size": [210, 46],
        "flags": {},
        "order": 2,
        "mode": 0,
        "inputs": [
            {"name": "pixels", "type": "IMAGE", "link": img_in},
            {"name": "vae", "type": "VAE", "link": vae_in},
        ],
        "outputs": [{"name": "LATENT", "type": "LATENT", "links": [latent_out]}],
        "properties": {"Node name for S&R": "VAEEncode"},
        "widgets_values": [],
    }


def _sampler(nid, model, pos, neg, latent, out, title, denoise, y):
    return {
        "id": nid,
        "type": "KSampler",
        "pos": [80, y],
        "size": [315, 474],
        "flags": {},
        "order": 5,
        "mode": 0,
        "inputs": [
            {"name": "model", "type": "MODEL", "link": model},
            {"name": "positive", "type": "CONDITIONING", "link": pos},
            {"name": "negative", "type": "CONDITIONING", "link": neg},
            {"name": "latent_image", "type": "LATENT", "link": latent},
            {"name": "seed", "type": "INT", "widget": {"name": "seed"}, "link": None},
            {"name": "steps", "type": "INT", "widget": {"name": "steps"}, "link": None},
            {"name": "cfg", "type": "FLOAT", "widget": {"name": "cfg"}, "link": None},
            {"name": "sampler_name", "type": "COMBO", "widget": {"name": "sampler_name"}, "link": None},
            {"name": "scheduler", "type": "COMBO", "widget": {"name": "scheduler"}, "link": None},
            {"name": "denoise", "type": "FLOAT", "widget": {"name": "denoise"}, "link": None},
        ],
        "outputs": [{"name": "LATENT", "type": "LATENT", "links": [out]}],
        "properties": {"Node name for S&R": "KSampler"},
        "title": title,
        "widgets_values": [0, "randomize", 28, 6.0, "euler", "normal", denoise],
    }


def _decode(nid, samples, vae, out):
    return {
        "id": nid,
        "type": "VAEDecode",
        "pos": [440, 160],
        "size": [210, 46],
        "flags": {},
        "order": 6,
        "mode": 0,
        "inputs": [
            {"name": "samples", "type": "LATENT", "link": samples},
            {"name": "vae", "type": "VAE", "link": vae},
        ],
        "outputs": [{"name": "IMAGE", "type": "IMAGE", "links": [out]}],
        "properties": {"Node name for S&R": "VAEDecode"},
        "widgets_values": [],
    }


def _save(nid, img, prefix):
    return {
        "id": nid,
        "type": "SaveImage",
        "pos": [700, 160],
        "size": [280, 58],
        "flags": {},
        "order": 7,
        "mode": 0,
        "inputs": [
            {"name": "images", "type": "IMAGE", "link": img},
            {"name": "filename_prefix", "type": "STRING", "widget": {"name": "filename_prefix"}, "link": None},
        ],
        "outputs": [],
        "properties": {"Node name for S&R": "SaveImage"},
        "widgets_values": [prefix],
    }


def _note(nid, text, pos):
    return {
        "id": nid,
        "type": "MarkdownNote",
        "pos": pos,
        "size": [480, 200],
        "flags": {},
        "order": 0,
        "mode": 0,
        "inputs": [],
        "outputs": [],
        "title": "说明",
        "properties": {},
        "widgets_values": [text],
        "color": "#432",
        "bgcolor": "#1a1a1a",
    }


def main():
    files = {
        "HunyuanDiT_图形合成_01_文生图.json": t2i_workflow(),
        "HunyuanDiT_图形合成_02_图生图.json": i2i_workflow(),
    }
    for name, data in files.items():
        text = json.dumps(data, ensure_ascii=False, indent=2)
        (REPO / name).write_text(text, encoding="utf-8")
        if COMFY.parent.exists():
            (COMFY / name).write_text(text, encoding="utf-8")

    combined = REPO / "HunyuanDiT_图形合成.json"
    if combined.exists():
        d = json.loads(combined.read_text(encoding="utf-8"))
        if d.get("extra") is None:
            d["extra"] = {}
        d["extra"]["workflow_note"] = (
            "已拆分为 HunyuanDiT_图形合成_01_文生图 与 _02_图生图，请分别 Queue，勿再一次跑整张。"
        )
        note = (
            "## 已拆分\n\n"
            "此合并版易误 Queue 两次（15~25 分钟）。请改用：\n"
            "- `HunyuanDiT_图形合成_01_文生图.json`\n"
            "- `HunyuanDiT_图形合成_02_图生图.json`"
        )
        found = False
        for n in d.get("nodes", []):
            if n.get("type") == "MarkdownNote":
                n["widgets_values"] = [note]
                found = True
                break
        if not found:
            d["nodes"].append(_note(98, note, [-900, -320]))
        text = json.dumps(d, ensure_ascii=False, indent=2)
        combined.write_text(text, encoding="utf-8")
        if COMFY.parent.exists():
            (COMFY / combined.name).write_text(text, encoding="utf-8")

    readme = REPO / "HunyuanDiT_图形合成_README.md"
    readme.write_text(
        """# HunyuanDiT 图形合成（已拆分）

| 文件 | 用途 | Queue |
|------|------|-------|
| `HunyuanDiT_图形合成_01_文生图.json` | 纯中文分层文生图 | **只开这个** |
| `HunyuanDiT_图形合成_02_图生图.json` | 参考图换背景/融氛围 | **只开这个** |
| `HunyuanDiT_图形合成.json` | 旧合并版（不推荐一次 Queue） | 勿用 |

## ② 图生图链路

`LoadImage` → `VAEEncode` → `KSampler` → `VAEDecode` → `SaveImage`

## 模型

`hunyuan_dit_comfyui/hunyuan_dit_1.2.safetensors` — `install/install_hunyuan_dit.ps1`

## 8GB

`--lowvram --cpu-vae`，单流程约 5~12 分钟。

## 重建

```powershell
python install/build_hunyuan_compose_split.py
```
""",
        encoding="utf-8",
    )
    print("ok")


if __name__ == "__main__":
    main()
