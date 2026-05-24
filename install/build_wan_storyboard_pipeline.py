"""Build wan视频流 storyboard workflows: FLUX keyframes + Wan segments + FLF GGUF."""
import copy
import json
import sys
import uuid
from pathlib import Path

_INST = Path(__file__).resolve().parent
sys.path.insert(0, str(_INST))
from repo_paths import REPO_WF, COMFY_WF  # noqa: E402

OUT = COMFY_WF / "wan视频流"
REPO_OUT = REPO_WF / "wan视频流"
FLF_SRC = Path(
    r"C:\ComfyUI\python_embeded\Lib\site-packages\comfyui_workflow_templates_media_video"
    r"\templates\video_wan2_2_14B_flf2v.json"
)
STABLE_I2V = COMFY_WF / "I2V_标准_图生视频_稳态少虚影.json"
if not STABLE_I2V.exists():
    STABLE_I2V = REPO_WF / "I2V_标准_图生视频_稳态少虚影.json"

Q = "Q3_K_S"
HIGH = f"wan2.2_i2v_high_noise_14B_{Q}.gguf"
LOW = f"wan2.2_i2v_low_noise_14B_{Q}.gguf"
TE = "umt5-xxl-encoder-Q4_K_S.gguf"
VAE = "wan_2.1_vae.safetensors"

SEG_PROMPT = (
    "Same person and scene. Static camera. Smooth natural transition toward the target pose, "
    "no sudden jump, no duplicate body, temporal consistency, subtle motion only, sharp focus."
)


def patch_unet(node, high, low):
    if node.get("type") != "UNETLoader":
        return
    vals = node.get("widgets_values") or []
    name = vals[0] if vals else ""
    if "high_noise" in name:
        node["widgets_values"] = [high]
    elif "low_noise" in name:
        node["widgets_values"] = [low]
    else:
        return
    node["type"] = "UnetLoaderGGUF"
    node["properties"]["Node name for S&R"] = "UnetLoaderGGUF"
    node["inputs"] = [i for i in node.get("inputs", []) if i.get("name") == "unet_name"]


def patch_clip(node, te):
    if node.get("type") != "CLIPLoader":
        return
    vals = node.get("widgets_values") or []
    if len(vals) >= 2 and vals[1] == "wan":
        node["type"] = "CLIPLoaderGGUF"
        node["widgets_values"] = [te, "wan"]
        node["properties"]["Node name for S&R"] = "CLIPLoaderGGUF"


def walk_gguf(obj):
    if isinstance(obj, dict):
        patch_unet(obj, HIGH, LOW)
        patch_clip(obj, TE)
        for v in obj.values():
            walk_gguf(v)
    elif isinstance(obj, list):
        for x in obj:
            walk_gguf(x)


def make_segment_wan(name: str, title: str, load_img: str, save_prefix: str, note: str) -> dict:
    data = json.loads(STABLE_I2V.read_text(encoding="utf-8"))
    data = copy.deepcopy(data)
    data["id"] = str(uuid.uuid4())
    for n in data["nodes"]:
        if n.get("id") == 200:
            n["title"] = f"上传首帧 · {title}"
            n["widgets_values"] = [load_img, "image"]
        if n.get("type") == "296b573f-1e7d-43df-a2df-925fe5e17063":
            w = n["widgets_values"]
            if isinstance(w, list) and len(w) >= 4:
                w[0] = SEG_PROMPT
                w[3] = 49
            n["title"] = title
        if n.get("id") == 201:
            n["widgets_values"] = [save_prefix, "auto", "auto"]
        if n.get("type") == "MarkdownNote":
            n["widgets_values"] = [note]
    data["groups"] = [{"id": 1, "title": f"Wan 分镜片段 · {title}", "bounding": [-460, 60, 1880, 960], "color": "#a33535", "font_size": 22, "flags": {}}]
    return data


def patch_flf_gguf(data: dict) -> None:
    walk_gguf(data)
    for n in data.get("nodes", []):
        if n.get("type") == "LoadImage":
            t = (n.get("title") or n.get("properties", {}).get("Node name for S&R") or "").lower()
            w = n.get("widgets_values") or []
            if "end" in str(w[0]).lower() or n.get("id") == 68:
                n["title"] = "② 尾帧 keyframe/kf_02.png"
                n["widgets_values"] = ["keyframe/kf_02.png", "image"]
            elif n.get("id") == 80 or "start" in t or n.get("mode") == 0:
                n["title"] = "① 首帧 keyframe/kf_01.png"
                n["widgets_values"] = ["keyframe/kf_01.png", "image"]
        if n.get("type") == "WanFirstLastFrameToVideo":
            w = n.get("widgets_values")
            if isinstance(w, list) and len(w) >= 3:
                w[0], w[1], w[2] = 768, 432, 49
        if n.get("type") == "SaveVideo":
            n["widgets_values"] = ["video/wan_storyboard/flf_segment", "auto", "auto"]
        if n.get("type") == "CLIPTextEncode" and "Positive" in (n.get("title") or ""):
            n["widgets_values"] = [SEG_PROMPT]
        n["mode"] = 0


def write_flux_keyframes():
    path = OUT / "01_FLUX_关键帧_三连图.json"
    content = FLUX_KEYFRAME_JSON.strip()
    path.write_text(content, encoding="utf-8")
    (REPO_OUT / path.name).write_text(content, encoding="utf-8")


FLUX_KEYFRAME_JSON = r'''
{
  "id": "flux-kf-chain-001",
  "revision": 0,
  "last_node_id": 24,
  "last_link_id": 30,
  "nodes": [
    {"id": 1, "type": "UNETLoader", "pos": [-900, 60], "size": [270, 82], "flags": {}, "order": 1, "mode": 0,
      "inputs": [{"name": "unet_name", "type": "COMBO", "widget": {"name": "unet_name"}, "link": null}, {"name": "weight_dtype", "type": "COMBO", "widget": {"name": "weight_dtype"}, "link": null}],
      "outputs": [{"name": "MODEL", "type": "MODEL", "links": [1, 16, 22]}],
      "properties": {"Node name for S&R": "UNETLoader"}, "widgets_values": ["flux1-dev-fp8.safetensors", "default"]},
    {"id": 2, "type": "DualCLIPLoader", "pos": [-900, 200], "size": [270, 130], "flags": {}, "order": 2, "mode": 0,
      "inputs": [{"name": "clip_name1", "type": "COMBO", "widget": {"name": "clip_name1"}, "link": null}, {"name": "clip_name2", "type": "COMBO", "widget": {"name": "clip_name2"}, "link": null}, {"name": "type", "type": "COMBO", "widget": {"name": "type"}, "link": null}, {"name": "device", "type": "COMBO", "widget": {"name": "device"}, "link": null}],
      "outputs": [{"name": "CLIP", "type": "CLIP", "links": [2, 3, 14, 15, 20, 21]}],
      "properties": {"Node name for S&R": "DualCLIPLoader"}, "widgets_values": ["clip_l.safetensors", "t5xxl_fp8_e4m3fn.safetensors", "flux", "default"]},
    {"id": 3, "type": "VAELoader", "pos": [-900, 380], "size": [270, 82], "flags": {}, "order": 3, "mode": 0,
      "inputs": [{"name": "vae_name", "type": "COMBO", "widget": {"name": "vae_name"}, "link": null}],
      "outputs": [{"name": "VAE", "type": "VAE", "links": [10, 11, 17, 18, 23, 24]}],
      "properties": {"Node name for S&R": "VAELoader"}, "widgets_values": ["ae.safetensors"]},
    {"id": 10, "type": "LoadImage", "pos": [-900, 520], "size": [300, 300], "flags": {}, "order": 0, "mode": 0,
      "inputs": [{"name": "image", "type": "COMBO", "widget": {"name": "image"}, "link": null}, {"name": "upload", "type": "IMAGEUPLOAD", "widget": {"name": "upload"}, "link": null}],
      "outputs": [{"name": "IMAGE", "type": "IMAGE", "links": [12]}, {"name": "MASK", "type": "MASK", "links": null}],
      "properties": {"Node name for S&R": "LoadImage"}, "title": "定妆参考图", "widgets_values": ["reference.png", "image"]},
    {"id": 5, "type": "CLIPTextEncode", "pos": [-520, 520], "size": [400, 100], "flags": {}, "order": 4, "mode": 0,
      "inputs": [{"name": "clip", "type": "CLIP", "link": 3}, {"name": "text", "type": "STRING", "widget": {"name": "text"}, "link": null}],
      "outputs": [{"name": "CONDITIONING", "type": "CONDITIONING", "links": [5]}],
      "properties": {"Node name for S&R": "CLIPTextEncode"}, "title": "负向",
      "widgets_values": ["ugly, deformed, identity change, different person, anime, thick lips, gore"]},
    {"id": 4, "type": "CLIPTextEncode", "pos": [-520, 40], "size": [420, 180], "flags": {}, "order": 5, "mode": 0,
      "inputs": [{"name": "clip", "type": "CLIP", "link": 2}, {"name": "text", "type": "STRING", "widget": {"name": "text"}, "link": null}],
      "outputs": [{"name": "CONDITIONING", "type": "CONDITIONING", "links": [13]}],
      "properties": {"Node name for S&R": "CLIPTextEncode"}, "title": "关键帧1·正面",
      "widgets_values": ["Same person as reference. Front facing, neutral standing, office corridor or bedroom scene, J-horror muted lighting, full body visible, cinematic photo, keep identity."]},
    {"id": 12, "type": "FluxGuidance", "pos": [-520, 230], "size": [270, 58], "flags": {}, "order": 6, "mode": 0,
      "inputs": [{"name": "conditioning", "type": "CONDITIONING", "link": 13}, {"name": "guidance", "type": "FLOAT", "widget": {"name": "guidance"}, "link": null}],
      "outputs": [{"name": "CONDITIONING", "type": "CONDITIONING", "links": [4]}],
      "properties": {"Node name for S&R": "FluxGuidance"}, "widgets_values": [3.7]},
    {"id": 11, "type": "VAEEncode", "pos": [-200, 520], "size": [210, 46], "flags": {}, "order": 7, "mode": 0,
      "inputs": [{"name": "pixels", "type": "IMAGE", "link": 12}, {"name": "vae", "type": "VAE", "link": 10}],
      "outputs": [{"name": "LATENT", "type": "LATENT", "links": [6]}],
      "properties": {"Node name for S&R": "VAEEncode"}, "widgets_values": []},
    {"id": 7, "type": "KSampler", "pos": [40, 120], "size": [315, 474], "flags": {}, "order": 8, "mode": 0,
      "inputs": [{"name": "model", "type": "MODEL", "link": 1}, {"name": "positive", "type": "CONDITIONING", "link": 4}, {"name": "negative", "type": "CONDITIONING", "link": 5}, {"name": "latent_image", "type": "LATENT", "link": 6}, {"name": "seed", "type": "INT", "widget": {"name": "seed"}, "link": null}, {"name": "steps", "type": "INT", "widget": {"name": "steps"}, "link": null}, {"name": "cfg", "type": "FLOAT", "widget": {"name": "cfg"}, "link": null}, {"name": "sampler_name", "type": "COMBO", "widget": {"name": "sampler_name"}, "link": null}, {"name": "scheduler", "type": "COMBO", "widget": {"name": "scheduler"}, "link": null}, {"name": "denoise", "type": "FLOAT", "widget": {"name": "denoise"}, "link": null}],
      "outputs": [{"name": "LATENT", "type": "LATENT", "links": [7]}],
      "properties": {"Node name for S&R": "KSampler"}, "title": "KF1 denoise 0.52", "widgets_values": [1001, "fixed", 28, 1.0, "euler", "simple", 0.52]},
    {"id": 8, "type": "VAEDecode", "pos": [400, 120], "size": [210, 46], "flags": {}, "order": 9, "mode": 0,
      "inputs": [{"name": "samples", "type": "LATENT", "link": 7}, {"name": "vae", "type": "VAE", "link": 11}],
      "outputs": [{"name": "IMAGE", "type": "IMAGE", "links": [8, 19]}],
      "properties": {"Node name for S&R": "VAEDecode"}, "widgets_values": []},
    {"id": 9, "type": "SaveImage", "pos": [650, 100], "size": [280, 58], "flags": {}, "order": 10, "mode": 0,
      "inputs": [{"name": "images", "type": "IMAGE", "link": 8}, {"name": "filename_prefix", "type": "STRING", "widget": {"name": "filename_prefix"}, "link": null}],
      "outputs": [], "properties": {"Node name for S&R": "SaveImage"}, "widgets_values": ["keyframe/kf_01"]},
    {"id": 14, "type": "CLIPTextEncode", "pos": [-520, 720], "size": [420, 160], "flags": {}, "order": 11, "mode": 0,
      "inputs": [{"name": "clip", "type": "CLIP", "link": 14}, {"name": "text", "type": "STRING", "widget": {"name": "text"}, "link": null}],
      "outputs": [{"name": "CONDITIONING", "type": "CONDITIONING", "links": [25]}],
      "properties": {"Node name for S&R": "CLIPTextEncode"}, "title": "关键帧2·微转",
      "widgets_values": ["Same person. Body turned 25 degrees to the right, same outfit and background as previous frame, gradual turn, J-horror lighting, keep face identity."]},
    {"id": 15, "type": "FluxGuidance", "pos": [-520, 900], "size": [270, 58], "flags": {}, "order": 12, "mode": 0,
      "inputs": [{"name": "conditioning", "type": "CONDITIONING", "link": 25}, {"name": "guidance", "type": "FLOAT", "widget": {"name": "guidance"}, "link": null}],
      "outputs": [{"name": "CONDITIONING", "type": "CONDITIONING", "links": [26]}],
      "properties": {"Node name for S&R": "FluxGuidance"}, "widgets_values": [3.7]},
    {"id": 13, "type": "VAEEncode", "pos": [-200, 800], "size": [210, 46], "flags": {}, "order": 13, "mode": 0,
      "inputs": [{"name": "pixels", "type": "IMAGE", "link": 19}, {"name": "vae", "type": "VAE", "link": 17}],
      "outputs": [{"name": "LATENT", "type": "LATENT", "links": [27]}],
      "properties": {"Node name for S&R": "VAEEncode"}, "widgets_values": []},
    {"id": 16, "type": "KSampler", "pos": [40, 720], "size": [315, 474], "flags": {}, "order": 14, "mode": 0,
      "inputs": [{"name": "model", "type": "MODEL", "link": 16}, {"name": "positive", "type": "CONDITIONING", "link": 26}, {"name": "negative", "type": "CONDITIONING", "link": 5}, {"name": "latent_image", "type": "LATENT", "link": 27}, {"name": "seed", "type": "INT", "widget": {"name": "seed"}, "link": null}, {"name": "steps", "type": "INT", "widget": {"name": "steps"}, "link": null}, {"name": "cfg", "type": "FLOAT", "widget": {"name": "cfg"}, "link": null}, {"name": "sampler_name", "type": "COMBO", "widget": {"name": "sampler_name"}, "link": null}, {"name": "scheduler", "type": "COMBO", "widget": {"name": "scheduler"}, "link": null}, {"name": "denoise", "type": "FLOAT", "widget": {"name": "denoise"}, "link": null}],
      "outputs": [{"name": "LATENT", "type": "LATENT", "links": [28]}],
      "properties": {"Node name for S&R": "KSampler"}, "title": "KF2 denoise 0.45", "widgets_values": [1002, "fixed", 28, 1.0, "euler", "simple", 0.45]},
    {"id": 17, "type": "VAEDecode", "pos": [400, 720], "size": [210, 46], "flags": {}, "order": 15, "mode": 0,
      "inputs": [{"name": "samples", "type": "LATENT", "link": 28}, {"name": "vae", "type": "VAE", "link": 18}],
      "outputs": [{"name": "IMAGE", "type": "IMAGE", "links": [29, 30]}],
      "properties": {"Node name for S&R": "VAEDecode"}, "widgets_values": []},
    {"id": 18, "type": "SaveImage", "pos": [650, 700], "size": [280, 58], "flags": {}, "order": 16, "mode": 0,
      "inputs": [{"name": "images", "type": "IMAGE", "link": 29}, {"name": "filename_prefix", "type": "STRING", "widget": {"name": "filename_prefix"}, "link": null}],
      "outputs": [], "properties": {"Node name for S&R": "SaveImage"}, "widgets_values": ["keyframe/kf_02"]},
    {"id": 20, "type": "CLIPTextEncode", "pos": [-520, 1100], "size": [420, 160], "flags": {}, "order": 17, "mode": 0,
      "inputs": [{"name": "clip", "type": "CLIP", "link": 20}, {"name": "text", "type": "STRING", "widget": {"name": "text"}, "link": null}],
      "outputs": [{"name": "CONDITIONING", "type": "CONDITIONING", "links": [31]}],
      "properties": {"Node name for S&R": "CLIPTextEncode"}, "title": "关键帧3·侧身",
      "widgets_values": ["Same person. Profile view about 50 degrees, same outfit and scene, continued turn, J-horror, keep identity, cinematic."]},
    {"id": 21, "type": "FluxGuidance", "pos": [-520, 1280], "size": [270, 58], "flags": {}, "order": 18, "mode": 0,
      "inputs": [{"name": "conditioning", "type": "CONDITIONING", "link": 31}, {"name": "guidance", "type": "FLOAT", "widget": {"name": "guidance"}, "link": null}],
      "outputs": [{"name": "CONDITIONING", "type": "CONDITIONING", "links": [32]}],
      "properties": {"Node name for S&R": "FluxGuidance"}, "widgets_values": [3.7]},
    {"id": 19, "type": "VAEEncode", "pos": [-200, 1180], "size": [210, 46], "flags": {}, "order": 19, "mode": 0,
      "inputs": [{"name": "pixels", "type": "IMAGE", "link": 30}, {"name": "vae", "type": "VAE", "link": 23}],
      "outputs": [{"name": "LATENT", "type": "LATENT", "links": [33]}],
      "properties": {"Node name for S&R": "VAEEncode"}, "widgets_values": []},
    {"id": 22, "type": "KSampler", "pos": [40, 1100], "size": [315, 474], "flags": {}, "order": 20, "mode": 0,
      "inputs": [{"name": "model", "type": "MODEL", "link": 22}, {"name": "positive", "type": "CONDITIONING", "link": 32}, {"name": "negative", "type": "CONDITIONING", "link": 5}, {"name": "latent_image", "type": "LATENT", "link": 33}, {"name": "seed", "type": "INT", "widget": {"name": "seed"}, "link": null}, {"name": "steps", "type": "INT", "widget": {"name": "steps"}, "link": null}, {"name": "cfg", "type": "FLOAT", "widget": {"name": "cfg"}, "link": null}, {"name": "sampler_name", "type": "COMBO", "widget": {"name": "sampler_name"}, "link": null}, {"name": "scheduler", "type": "COMBO", "widget": {"name": "scheduler"}, "link": null}, {"name": "denoise", "type": "FLOAT", "widget": {"name": "denoise"}, "link": null}],
      "outputs": [{"name": "LATENT", "type": "LATENT", "links": [34]}],
      "properties": {"Node name for S&R": "KSampler"}, "title": "KF3 denoise 0.42", "widgets_values": [1003, "fixed", 28, 1.0, "euler", "simple", 0.42]},
    {"id": 23, "type": "VAEDecode", "pos": [400, 1100], "size": [210, 46], "flags": {}, "order": 21, "mode": 0,
      "inputs": [{"name": "samples", "type": "LATENT", "link": 34}, {"name": "vae", "type": "VAE", "link": 24}],
      "outputs": [{"name": "IMAGE", "type": "IMAGE", "links": [35]}],
      "properties": {"Node name for S&R": "VAEDecode"}, "widgets_values": []},
    {"id": 24, "type": "SaveImage", "pos": [650, 1080], "size": [280, 58], "flags": {}, "order": 22, "mode": 0,
      "inputs": [{"name": "images", "type": "IMAGE", "link": 35}, {"name": "filename_prefix", "type": "STRING", "widget": {"name": "filename_prefix"}, "link": null}],
      "outputs": [], "properties": {"Node name for S&R": "SaveImage"}, "widgets_values": ["keyframe/kf_03"]},
    {"id": 99, "type": "MarkdownNote", "pos": [-900, -120], "size": [520, 320], "flags": {}, "order": 0, "mode": 0, "inputs": [], "outputs": [],
      "title": "分镜关键帧说明", "properties": {},
      "widgets_values": ["## FLUX 三连关键帧\n1. 上传 reference 定妆图\n2. Queue 一次 → 输出 `ComfyUI/output/keyframe/kf_01|02|03.png`\n3. 复制到 `ComfyUI/input/keyframe/` 供 Wan 使用\n\n也可用 SDXL：用 `日系惊悚_场景` 文生空镜 + I2I 做人景融合。\n\n**转身**：KF1 正面 → KF2 25° → KF3 侧身；denoise 逐级降低保脸。"],
      "color": "#432", "bgcolor": "#111"}
  ],
  "links": [
    [1,1,0,7,0,"MODEL"],[16,1,0,16,0,"MODEL"],[22,1,0,22,0,"MODEL"],
    [2,2,0,4,0,"CLIP"],[3,2,0,5,0,"CLIP"],[14,2,0,14,0,"CLIP"],[20,2,0,20,0,"CLIP"],
    [4,12,0,7,1,"CONDITIONING"],[13,4,0,12,0,"CONDITIONING"],[26,15,0,16,1,"CONDITIONING"],[32,21,0,22,1,"CONDITIONING"],
    [5,5,0,7,2,"CONDITIONING"],[6,11,0,7,3,"LATENT"],[7,7,0,8,0,"LATENT"],[8,8,0,9,0,"IMAGE"],
    [10,3,0,11,1,"VAE"],[11,3,0,8,1,"VAE"],[12,10,0,11,0,"IMAGE"],
    [17,3,0,13,1,"VAE"],[18,3,0,17,1,"VAE"],[19,8,0,13,0,"IMAGE"],
    [25,14,0,15,0,"CONDITIONING"],[26,15,0,16,1,"CONDITIONING"],[27,13,0,16,3,"LATENT"],[28,16,0,17,0,"LATENT"],[29,17,0,18,0,"IMAGE"],
    [23,3,0,19,1,"VAE"],[24,3,0,23,1,"VAE"],[30,17,0,19,0,"IMAGE"],
    [31,20,0,21,0,"CONDITIONING"],[32,21,0,22,1,"CONDITIONING"],[33,19,0,22,3,"LATENT"],[34,22,0,23,0,"LATENT"],[35,23,0,24,0,"IMAGE"]
  ],
  "groups": [{"id": 1, "title": "01 FLUX 关键帧链 · 正面→微转→侧身", "bounding": [-940, -140, 1920, 1500], "color": "#8A5", "font_size": 22, "flags": {}}],
  "config": {}, "extra": {"ds": {"scale": 0.55, "offset": [1100, 200]}}, "version": 0.4
}
'''


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    REPO_OUT.mkdir(parents=True, exist_ok=True)

    write_flux_keyframes()

    segments = [
        ("02_Wan_片段_A_kf01到kf02", "A: kf01→kf02", "keyframe/kf_01.png", "video/wan_storyboard/seg_A", "首尾帧补间见 03；或本片段仅作预览。"),
        ("02_Wan_片段_B_kf02到kf03", "B: kf02→kf03", "keyframe/kf_02.png", "video/wan_storyboard/seg_B", "上一段尾帧可替代 kf_02 作首帧。"),
        ("02_Wan_单帧_稳态_kf03", "C: kf03 定帧", "keyframe/kf_03.png", "video/wan_storyboard/seg_C", "末帧微动，可选。"),
    ]
    for fname, title, img, prefix, note in segments:
        d = make_segment_wan(fname, title, img, prefix, f"## {title}\n{note}\nlength=49, 768×432, LoRA 0.6")
        text = json.dumps(d, ensure_ascii=False, indent=2)
        (OUT / f"{fname}.json").write_text(text, encoding="utf-8")
        (REPO_OUT / f"{fname}.json").write_text(text, encoding="utf-8")

    if FLF_SRC.exists():
        flf = json.loads(FLF_SRC.read_text(encoding="utf-8"))
        flf = copy.deepcopy(flf)
        patch_flf_gguf(flf)
        flf_text = json.dumps(flf, ensure_ascii=False, indent=2)
        (OUT / "03_Wan_首尾帧_补间_GGUF.json").write_text(flf_text, encoding="utf-8")
        (REPO_OUT / "03_Wan_首尾帧_补间_GGUF.json").write_text(flf_text, encoding="utf-8")

    import shutil
    for name in ("00_分镜流程说明.md", "concat_segments.ps1"):
        src = REPO_OUT / name
        if src.exists():
            shutil.copy(src, OUT / name)

    print("built ok:", str(OUT).encode("ascii", "replace").decode())


if __name__ == "__main__":
    main()
