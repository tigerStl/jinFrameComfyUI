#!/usr/bin/env python3
"""Verify ComfyUI models match MODELS.lock.json (SHA256 + size).

Usage:
  python install/verify_models.py
  python install/verify_models.py --comfy-root D:\\ComfyUI\\ComfyUI
  python install/verify_models.py --pack hunyuan_dit
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_INST = Path(__file__).resolve().parent
sys.path.insert(0, str(_INST))

from models_lock import load_lock, verify_file  # noqa: E402


def _model_path(comfy_models: Path, entry: dict) -> Path:
    rel = entry.get("dir", "")
    name = entry["name"]
    return comfy_models / rel / name if rel else comfy_models / name


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify locked model files under ComfyUI/models")
    ap.add_argument("--comfy-root", default=os.environ.get("COMFYUI_ROOT", r"C:\ComfyUI\ComfyUI"))
    ap.add_argument("--pack", help="Only verify files in this pack_id")
    ap.add_argument("--id", help="Only verify this file id")
    args = ap.parse_args()

    lock = load_lock()
    comfy_models = Path(args.comfy_root).resolve() / "models"
    repo_root = Path(__file__).resolve().parent.parent
    distill = repo_root / "distill_loras"

    ok_count = 0
    fail_count = 0
    skip_count = 0

    print(f"Lock: {lock.get('locked_at')}  ComfyUI models: {comfy_models}\n")

    for entry in lock.get("files", []):
        if args.pack and entry.get("pack_id") != args.pack:
            continue
        if args.id and entry.get("id") != args.id:
            continue

        fid = entry["id"]
        path = _model_path(comfy_models, entry)
        if not path.is_file() and entry.get("source") == "repo_distill_loras":
            path = distill / entry["name"]

        if not path.is_file() and entry.get("id") == "ltx_distill_lora":
            alt = distill / entry["name"]
            if alt.is_file():
                path = alt

        if not entry.get("sha256"):
            print(f"[SKIP] {fid}: no sha256 in lock")
            skip_count += 1
            continue

        ok, msg = verify_file(path, entry)
        if ok:
            print(f"[OK]   {fid}  {entry['name']}")
            ok_count += 1
        else:
            rev = entry.get("revision", "?")[:12]
            print(f"[FAIL] {fid}  {msg}  (rev={rev}...)")
            print(f"       path: {path}")
            fail_count += 1

    print(f"\nSummary: {ok_count} ok, {fail_count} fail, {skip_count} skip")
    if fail_count:
        print("Fix: python install/download_from_lock.py --id <id>")
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
