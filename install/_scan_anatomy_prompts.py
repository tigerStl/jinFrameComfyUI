"""One-off scan for anatomical explicit terms in workflow JSON."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

_INST = Path(__file__).resolve().parent
sys.path.insert(0, str(_INST))
from repo_paths import COMFY_WF, REPO_WF  # noqa: E402

# Keep in sync with sanitize_workflow_prompts.ANATOMY_EXPLICIT_RE
ZH_RE = re.compile(
    r"乳房|乳头|阴部|私处|生殖器|阴茎|阴道|阴唇|乳晕|阴户|睾丸|龟头|阴囊|会阴|"
    r"露点|巨乳|爆乳|酥胸|乳沟|下体|胯下|走光|阴毛"
)
EN_RE = re.compile(
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
    r")\b",
    re.I,
)


def hits(text: str) -> list[str]:
    if not text:
        return []
    found = []
    for m in ZH_RE.finditer(text):
        found.append(m.group(0))
    for m in EN_RE.finditer(text):
        found.append(m.group(0))
    return found


def scan_file(path: Path) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    raw = path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = None
    if isinstance(data, dict) and "nodes" in data:
        for node in data.get("nodes", []):
            if not isinstance(node, dict):
                continue
            w = node.get("widgets_values")
            if isinstance(w, list):
                for i, v in enumerate(w):
                    if isinstance(v, str):
                        for h in hits(v):
                            out.append((f"node {node.get('id')} w[{i}]", h, v[:120]))
    elif isinstance(data, dict):
        for nid, node in data.items():
            if isinstance(node, dict):
                inp = node.get("inputs") or {}
                tx = inp.get("text")
                if isinstance(tx, str):
                    for h in hits(tx):
                        out.append((f"api {nid}", h, tx[:120]))
    if not out:
        for h in hits(raw):
            if h == "三点" and "凌晨三点" in raw:
                continue
            out.append(("raw", h, ""))
    return out


def main() -> None:
    roots = [REPO_WF, COMFY_WF]
    any_hit = False
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.json")):
            rows = scan_file(path)
            if rows:
                any_hit = True
                print(path.as_posix())
                for loc, word, snip in rows:
                    print(f"  {loc}: {word} | {snip!r}")
    if not any_hit:
        print("no anatomical explicit terms found")


if __name__ == "__main__":
    main()
