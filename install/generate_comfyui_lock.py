#!/usr/bin/env python3
"""Generate COMFYUI.lock.json from a working local ComfyUI install.

Usage:
  python install/generate_comfyui_lock.py --comfy-root C:\\ComfyUI\\ComfyUI
"""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _git_head(path: Path) -> tuple[str | None, str | None]:
    if not (path / ".git").is_dir():
        return None, None
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path, text=True).strip()
    url = subprocess.check_output(["git", "remote", "get-url", "origin"], cwd=path, text=True).strip()
    return sha, url


def _git_subject(path: Path) -> str:
    return subprocess.check_output(["git", "log", "-1", "--format=%s"], cwd=path, text=True).strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--comfy-root", default=r"C:\ComfyUI\ComfyUI")
    args = ap.parse_args()

    comfy = Path(args.comfy_root).resolve()
    if not (comfy / "main.py").is_file():
        raise SystemExit(f"Not a ComfyUI folder: {comfy}")

    sha, url = _git_head(comfy)
    lock = {
        "lock_version": 1,
        "locked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "description": "Generated from local install. ComfyUI is not committed to Git.",
        "default_comfy_root": str(comfy),
        "comfyui": {
            "repo": url or "",
            "revision": sha or "",
            "label": _git_subject(comfy) if sha else "",
        },
        "custom_nodes": [],
    }

    cn = comfy / "custom_nodes"
    for child in sorted(cn.iterdir()) if cn.is_dir() else []:
        if not child.is_dir() or child.name.startswith("__"):
            continue
        csha, curl = _git_head(child)
        if csha:
            lock["custom_nodes"].append(
                {
                    "name": child.name,
                    "repo": curl or "",
                    "revision": csha,
                    "required": child.name in ("ComfyUI-Manager", "ComfyUI-GGUF", "ComfyUI_LTX2_SM"),
                }
            )

    out = REPO_ROOT / "COMFYUI.lock.json"
    with out.open("w", encoding="utf-8") as f:
        json.dump(lock, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
