#!/usr/bin/env python3
"""Download model file(s) using pinned URLs from MODELS.lock.json.

Usage:
  python install/download_from_lock.py --pack hunyuan_dit
  python install/download_from_lock.py --id hunyuan12
  python install/download_from_lock.py --all
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import urllib.request
from pathlib import Path

_INST = Path(__file__).resolve().parent
sys.path.insert(0, str(_INST))

from models_lock import load_lock, sha256_file, verify_file  # noqa: E402


def _dest(comfy_models: Path, entry: dict) -> Path:
    rel = entry.get("dir", "")
    name = entry["name"]
    return comfy_models / rel / name if rel else comfy_models / name


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "JinFrameLockedDownload/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp, part.open("wb") as f:
        while True:
            chunk = resp.read(8 * 1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
    if dest.exists():
        dest.unlink()
    shutil.move(str(part), str(dest))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--comfy-root", default=os.environ.get("COMFYUI_ROOT", r"C:\ComfyUI\ComfyUI"))
    ap.add_argument("--pack", action="append", help="pack_id (repeatable)")
    ap.add_argument("--id", action="append", help="file id (repeatable)")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--force", action="store_true", help="Re-download even if verify passes")
    args = ap.parse_args()

    lock = load_lock()
    comfy_models = Path(args.comfy_root).resolve() / "models"
    repo_root = Path(__file__).resolve().parent.parent
    distill = repo_root / "distill_loras"

    targets: list[dict] = []
    for entry in lock.get("files", []):
        if args.all:
            targets.append(entry)
        elif args.id and entry["id"] in args.id:
            targets.append(entry)
        elif args.pack and entry.get("pack_id") in args.pack:
            targets.append(entry)

    if not targets:
        print("Specify --pack, --id, or --all", file=sys.stderr)
        return 2

    errors = 0
    for entry in targets:
        fid = entry["id"]
        dest = _dest(comfy_models, entry)

        if not args.force:
            ok, msg = verify_file(dest, entry)
            if ok:
                print(f"[skip] {fid}: already verified ({msg})")
                continue

        url = (entry.get("url") or "").strip()
        if not url and entry.get("id") == "ltx_distill_lora":
            src = distill / entry["name"]
            if not src.is_file():
                print(f"[err] {fid}: missing {src}", file=sys.stderr)
                errors += 1
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            print(f"[copy] {fid} <- distill_loras")
        elif not url:
            print(f"[err] {fid}: no pinned url", file=sys.stderr)
            errors += 1
            continue
        else:
            rev = entry.get("revision", "?")[:12]
            print(f"[dl] {fid} rev={rev}...")
            try:
                _download(url, dest)
            except Exception as e:
                print(f"[err] {fid}: {e}", file=sys.stderr)
                errors += 1
                continue

        ok, msg = verify_file(dest, entry)
        if ok:
            print(f"[ok] {fid} sha256={entry['sha256'][:16]}...")
        else:
            print(f"[fail] {fid} after download: {msg}", file=sys.stderr)
            if dest.is_file():
                print(f"       actual sha256={sha256_file(dest)[:16]}...", file=sys.stderr)
            errors += 1

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
