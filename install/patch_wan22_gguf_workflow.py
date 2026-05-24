"""Patch official Wan 2.2 I2V blueprint for GGUF loaders."""
import argparse
import copy
import json
from pathlib import Path

ROOT = Path(r"C:\ComfyUI\ComfyUI")
SRC = ROOT / "blueprints" / "Image to Video (Wan 2.2).json"
DST = ROOT / "user" / "default" / "workflows" / "Wan22_I2V_GGUF_8GB.json"


def patch_unet(node: dict, high: str, low: str) -> None:
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
    node["title"] = "Unet GGUF " + ("High" if "high" in name else "Low")
    node["properties"]["Node name for S&R"] = "UnetLoaderGGUF"
    node["inputs"] = [
        inp for inp in node.get("inputs", []) if inp.get("name") == "unet_name"
    ]


def patch_clip(node: dict, te: str) -> None:
    if node.get("type") != "CLIPLoader":
        return
    vals = node.get("widgets_values") or []
    if len(vals) >= 2 and vals[1] == "wan":
        node["type"] = "CLIPLoaderGGUF"
        node["widgets_values"] = [te, "wan"]
        node["properties"]["Node name for S&R"] = "CLIPLoaderGGUF"
        node["title"] = "CLIP GGUF (umt5)"


def walk(obj, high: str, low: str, te: str) -> None:
    if isinstance(obj, dict):
        if obj.get("type") == "UNETLoader":
            patch_unet(obj, high, low)
        elif obj.get("type") == "CLIPLoader":
            patch_clip(obj, te)
        for v in obj.values():
            walk(v, high, low, te)
    elif isinstance(obj, list):
        for item in obj:
            walk(item, high, low, te)


def patch_top_widgets(data: dict, high: str, low: str, te: str, vae: str) -> None:
    for node in data.get("nodes", []):
        w = node.get("widgets_values")
        if not isinstance(w, list):
            continue
        # Root proxy node: prompt, w, h, length, seeds, high_unet, high_lora, low_unet, low_lora, clip, vae
        if len(w) >= 12 and isinstance(w[6], str) and "wan2.2_i2v" in w[6]:
            w[6] = high
            w[8] = low
            w[10] = te
            w[11] = vae
            w[1] = 832
            w[2] = 480
            w[3] = 65
            continue
        title = (node.get("title") or "").lower()
        if "low_noise_unet" in str(node.get("inputs", [])) or "low_noise" in title:
            if len(w) >= 1 and isinstance(w[0], str) and "wan2" in w[0]:
                w[0] = low
        if "high_noise" in title or "high_noise_unet" in str(node.get("inputs", [])):
            if len(w) >= 1 and isinstance(w[0], str) and "wan2" in w[0]:
                w[0] = high
        if node.get("inputs") and any(i.get("name") == "clip_name" for i in node["inputs"]):
            if w and isinstance(w[0], str) and "umt5" in w[0]:
                w[0] = te
        if node.get("inputs") and any(i.get("name") == "vae_name" for i in node["inputs"]):
            if w and isinstance(w[0], str) and "wan" in w[0]:
                w[0] = vae


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--quant", default="Q3_K_S")
    args = p.parse_args()
    q = args.quant

    high = f"wan2.2_i2v_high_noise_14B_{q}.gguf"
    low = f"wan2.2_i2v_low_noise_14B_{q}.gguf"
    te = "umt5-xxl-encoder-Q4_K_S.gguf"
    vae = "wan_2.1_vae.safetensors"

    data = json.loads(SRC.read_text(encoding="utf-8"))
    data = copy.deepcopy(data)
    walk(data, high, low, te)
    patch_top_widgets(data, high, low, te, vae)

    if "groups" in data and data["groups"]:
        data["groups"][0]["title"] = f"Wan 2.2 I2V GGUF ({q}) — 8GB: 832x480, lowvram"
        data["groups"][0]["color"] = "#a33535"

    DST.parent.mkdir(parents=True, exist_ok=True)
    DST.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {DST}")


if __name__ == "__main__":
    main()
