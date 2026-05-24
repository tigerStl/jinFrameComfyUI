"""Scan workflow JSON and replace NSFW / suggestive positive prompts with safe defaults."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_INST = Path(__file__).resolve().parent
sys.path.insert(0, str(_INST))
from repo_paths import COMFY_WF, REPO_WF  # noqa: E402

# LTX / generic video T2V default (empty positive in official templates)
DEFAULT_LTX_T2V_POSITIVE = ""

DEFAULT_PORTRAIT_ZH = (
    "悬疑电影静帧，一位27岁中国大陆汉族女性，鹅蛋脸，薄唇，黑色长发，白衬衫，"
    "站在老旧居民楼楼梯间，冷色荧光灯，低饱和度，眼神疏离，电影感构图，高清摄影，"
    "平静克制表情，非动漫非插画。"
)

DEFAULT_PORTRAIT_EN = (
    "RAW photo, masterpiece, best quality, mainland chinese woman, 27 years old, "
    "oval face, thin lips, black hair, white blouse, grey pencil skirt, "
    "chinese apartment stairwell, cold fluorescent light, cinematic portrait, "
    "photorealistic, calm neutral expression"
)

DEFAULT_HUNYUAN_COMPOSE_T2I = (
    "高清摄影，电影静帧，日系心理惊悚空镜，低饱和冷色荧光灯，非血腥，\n"
    "【主体】一位27岁中国大陆汉族女性，鹅蛋脸，薄唇，黑色中长发，白衬衫与灰色铅笔裙，\n"
    "【环境】中国大陆老旧居民楼楼梯间，斑驳墙面，金属扶手，\n"
    "【光影】冷色荧光灯，低饱和度，轻微雾气，\n"
    "【构图】中景，浅景深，人物偏左，右侧留白，悬疑氛围"
)

DEFAULT_HUNYUAN_COMPOSE_I2I = (
    "保持参考图中人物身份、脸型与姿势不变。\n"
    "【合成目标】仅替换背景为惊悚场景（走廊/楼梯间等），冷色荧光灯，低饱和度。\n"
    "【氛围】悬疑电影感，高清摄影，非动漫。"
)

NSFW_POSITIVE_RE = re.compile(
    r"(futanari|masturbat|underboob|penis|testicle|orgasm|\bcum\b|"
    r"porn|hentai|xxx|nude|nsfw|erotic|sex scene|topless|blowjob|handjob|"
    r"stripper|bdsm|bondage|"
    r"all naked|takes off her cloth|touches her nipples|"
    r"色情|裸体|裸照|性交|做爱|巨乳|乳沟|比基尼|情趣|露骨|走光|湿身诱惑|"
    r"脱掉.*上衣|抚摸.*乳房|露出.*乳房)",
    re.I,
)

# 露骨解剖 / 性器官 — 中文 + 英文（含 nipple、breast、genital 等，正向命中则替换）
ANATOMY_EXPLICIT_RE = re.compile(
    r"(乳房|乳头|阴部|私处|生殖器|阴茎|阴道|阴唇|乳晕|阴户|睾丸|龟头|阴囊|会阴|"
    r"阴毛|下体|胯下|露点|爆乳|酥胸|"
    r"\b(?:"
    r"breast|breasts|nipple|nipples|areola|areolas|areole|"
    r"mammary|mammaries|bosom|cleavage|underboob|underboobs|sideboob|"
    r"genital|genitals|genitalia|vulva|vagina|vaginal|penis|phallus|"
    r"dick|cock|glans|testicle|testicles|scrotum|ballsack|ball\s*sack|"
    r"pubic|pubes|pussy|cunt|clitoris|clit|labia|labial|"
    r"anus|anal|butthole|rectum|"
    r"boobs|boob|tits|titty|titties|"
    r"crotch|groin|pelvis|pelvic|spread\s+legs|"
    r"exposed\s+chest|bare\s+chest|bare\s+breasts|topless"
    r")\b)",
    re.I,
)

SUGGESTIVE_POSITIVE_RE = re.compile(
    r"(暧昧|含蓄暧昧|悬疑暧昧|暧昧镜头|暧昧张力|非露骨|"
    r"intimate tension|subtle intimate|boudoir|pin-?up|"
    r"sexy sultry|seductive pose|lingerie model)",
    re.I,
)

NEG_HINT_RE = re.compile(r"(负向|negative|#323)", re.I)

DEFAULT_I2V_POSITIVE = (
    "自然细微动作，镜头稳定，保持人物身份与画面一致，无变形、无重影、无多余肢体。"
)

PROMPT_NODE_TYPES = frozenset(
    {
        "CLIPTextEncode",
        "CLIPTextEncodeFlux",
        "CLIPTextEncodeSDXL",
        "CLIPTextEncodeHunyuanDiT",
        "LTX2_SM_ENCODER",
        "LTXVConditioning",
        "WanImageToVideo",
        "WanTextEncode",
    }
)


def looks_like_negative_prompt(text: str) -> bool:
    """Short anti-NSFW / quality strings without a scene description."""
    if len(text) > 320:
        return False
    if re.search(
        r"(worst quality|low quality|ugly|deformed|nsfw|nude|porn|explicit|"
        r"丑陋|变形|低质量|裸露|色情)",
        text,
        re.I,
    ) and not re.search(
        r"(masterpiece|best quality|RAW photo|高清|摄影|portrait|1girl|"
        r"【主体】|悬疑电影|cinematic still)",
        text,
        re.I,
    ):
        return True
    return False


def is_negative_node(node: dict) -> bool:
    color = str(node.get("color", ""))
    title = str(node.get("title") or node.get("properties", {}).get("Node name for S&R") or "")
    if color == "#323" or NEG_HINT_RE.search(title):
        return True
    widgets = node.get("widgets_values")
    if isinstance(widgets, list) and widgets and isinstance(widgets[0], str):
        return looks_like_negative_prompt(widgets[0])
    return False


def pick_default(text: str, path: Path) -> str:
    name = path.name.lower()
    if "i2v" in name or "图生视频" in name or "image2v" in name:
        return DEFAULT_I2V_POSITIVE if re.search(r"[\u4e00-\u9fff]", text) else DEFAULT_I2V_POSITIVE
    if "ltx23" in name or "ltx_" in name or "ltx云" in path.parts or "ltx" in name:
        return DEFAULT_LTX_T2V_POSITIVE
    if "图形合成" in name or "compose" in name:
        if "02" in name or "图生图" in name or "i2i" in name:
            return DEFAULT_HUNYUAN_COMPOSE_I2I
        return DEFAULT_HUNYUAN_COMPOSE_T2I
    if "hunyuan" in name or "中国风格" in name:
        return DEFAULT_PORTRAIT_ZH
    if re.search(r"[\u4e00-\u9fff]", text):
        return DEFAULT_PORTRAIT_ZH
    return DEFAULT_PORTRAIT_EN


def should_sanitize_positive(text: str) -> bool:
    if not text or not text.strip():
        return False
    return bool(
        NSFW_POSITIVE_RE.search(text)
        or SUGGESTIVE_POSITIVE_RE.search(text)
        or ANATOMY_EXPLICIT_RE.search(text)
    )


def _sanitize_node_list(nodes: list, path: Path) -> int:
    changed = 0
    for node in nodes:
        if not isinstance(node, dict):
            continue
        if is_negative_node(node):
            continue
        ntype = node.get("type")
        widgets = node.get("widgets_values")
        if not isinstance(widgets, list):
            continue
        if ntype in PROMPT_NODE_TYPES:
            indices = range(len(widgets))
        else:
            indices = [
                i for i, v in enumerate(widgets) if isinstance(v, str) and len(v) > 12
            ]
        for i in indices:
            text = widgets[i] if isinstance(widgets[i], str) else ""
            if not should_sanitize_positive(text):
                continue
            widgets[i] = pick_default(text, path)
            changed += 1
    return changed


def sanitize_canvas_workflow(data: dict, path: Path) -> int:
    changed = 0
    nodes = data.get("nodes")
    if isinstance(nodes, list):
        changed += _sanitize_node_list(nodes, path)
    defs = data.get("definitions")
    if isinstance(defs, dict):
        for sub in defs.get("subgraphs") or []:
            if isinstance(sub, dict) and isinstance(sub.get("nodes"), list):
                changed += _sanitize_node_list(sub["nodes"], path)
    return changed


def sanitize_api_workflow(data: dict, path: Path) -> int:
    changed = 0
    for node in data.values():
        if not isinstance(node, dict):
            continue
        if node.get("class_type") not in PROMPT_NODE_TYPES:
            continue
        inp = node.get("inputs")
        if not isinstance(inp, dict):
            continue
        text = inp.get("text")
        if not isinstance(text, str):
            continue
        meta = node.get("_meta") or {}
        title = str(meta.get("title", ""))
        if NEG_HINT_RE.search(title):
            continue
        if not should_sanitize_positive(text):
            continue
        inp["text"] = pick_default(text, path)
        changed += 1
    return changed


def sanitize_file(path: Path) -> int:
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    if isinstance(data, dict) and "nodes" in data:
        n = sanitize_canvas_workflow(data, path)
    elif isinstance(data, dict):
        n = sanitize_api_workflow(data, path)
    else:
        return 0
    if n:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return n


def scan_roots(roots: list[Path]) -> tuple[int, int]:
    total_files = 0
    total_nodes = 0
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.json")):
            n = sanitize_file(path)
            if n:
                total_files += 1
                total_nodes += n
                try:
                    rel = path.relative_to(root.parent)
                except ValueError:
                    rel = path
                line = f"sanitized {n} node(s): {rel.as_posix()}"
                print(line.encode("ascii", errors="backslashreplace").decode("ascii"))
    return total_files, total_nodes


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--comfy",
        action="store_true",
        help="Also sanitize C:\\ComfyUI\\...\\user\\default\\workflows",
    )
    args = p.parse_args()
    roots = [REPO_WF]
    if args.comfy:
        roots.append(COMFY_WF)
    files, nodes = scan_roots(roots)
    print(f"done: {files} file(s), {nodes} positive prompt(s) replaced")


if __name__ == "__main__":
    main()
