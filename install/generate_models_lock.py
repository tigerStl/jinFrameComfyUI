#!/usr/bin/env python3
"""Generate MODELS.lock.json from models_manifest.json + HF metadata + local files.

Usage:
  python install/generate_models_lock.py
  python install/generate_models_lock.py --comfy-root C:\\ComfyUI\\ComfyUI
  python install/generate_models_lock.py --from-local-only
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_INST = Path(__file__).resolve().parent
sys.path.insert(0, str(_INST))

from models_lock import (  # noqa: E402
    REPO_ROOT,
    lock_path,
    parse_hf_url,
    pinned_url,
    sha256_file,
)

try:
    from huggingface_hub import HfApi
except ImportError:
    print("pip install huggingface_hub", file=sys.stderr)
    raise


def _manifest_path() -> Path:
    return REPO_ROOT / "comfyui_extension" / "ComfyUI_JinFrameAssistant" / "models_manifest.json"


# Manifest URLs that point at the wrong HF repo; lock uses these instead.
_HF_OVERRIDES: dict[str, tuple[str, str]] = {
    "ae": ("black-forest-labs/FLUX.1-dev", "ae.safetensors"),
}


def _local_path(comfy_models: Path, finfo: dict) -> Path:
    rel = finfo.get("dir", "")
    name = finfo["name"]
    return comfy_models / rel / name if rel else comfy_models / name


def _hf_metadata(repo_id: str, hf_path: str, revision: str = "main") -> dict:
    api = HfApi()
    repo = api.repo_info(repo_id, revision=revision)
    commit_oid = repo.sha

    infos = api.get_paths_info(repo_id, [hf_path], repo_type="model", revision=commit_oid)
    if not infos:
        raise FileNotFoundError(f"{repo_id}/{hf_path} @ {commit_oid}")
    info = infos[0]
    size = int(getattr(info, "size", 0) or 0)
    lfs = getattr(info, "lfs", None)
    sha256 = None
    if lfs is not None:
        sha256 = getattr(lfs, "sha256", None)
        if sha256:
            sha256 = str(sha256).lower()
    return {
        "revision": commit_oid,
        "size_bytes": size,
        "sha256": sha256 if sha256 and len(sha256) == 64 else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--comfy-root", default=os.environ.get("COMFYUI_ROOT", r"C:\ComfyUI\ComfyUI"))
    ap.add_argument(
        "--from-local-only",
        action="store_true",
        help="Only hash files already on disk; skip HF API (offline)",
    )
    args = ap.parse_args()

    manifest_path = _manifest_path()
    with manifest_path.open(encoding="utf-8") as f:
        manifest = json.load(f)

    comfy_models = Path(args.comfy_root).resolve() / "models"
    files_out: list[dict] = []

    for pack in manifest.get("packs", []):
        for finfo in pack.get("files", []):
            fid = finfo["id"]
            entry: dict = {
                "id": fid,
                "pack_id": pack["id"],
                "name": finfo["name"],
                "dir": finfo.get("dir", ""),
                "min_mb": finfo.get("min_mb"),
            }

            url = (finfo.get("url") or "").strip()
            local = _local_path(comfy_models, finfo)
            repo_lora = REPO_ROOT / "distill_loras" / finfo["name"]

            if not url and fid == "ltx_distill_lora":
                src = repo_lora if repo_lora.is_file() else local
                entry["source"] = "repo_distill_loras" if repo_lora.is_file() else "comfyui_models"
                entry["url"] = ""
                entry["revision"] = "local"
                if src.is_file():
                    entry["size_bytes"] = src.stat().st_size
                    entry["sha256"] = sha256_file(src)
                    print(f"[local] {fid} sha256={entry['sha256'][:16]}...")
                else:
                    print(f"[warn] {fid}: missing {repo_lora}", file=sys.stderr)
                files_out.append(entry)
                continue

            if not url:
                print(f"[skip] {fid}: no url", file=sys.stderr)
                continue

            parsed = parse_hf_url(url)
            if fid in _HF_OVERRIDES:
                repo_id, hf_path = _HF_OVERRIDES[fid]
                parsed = (repo_id, "main", hf_path)

            if not parsed and not args.from_local_only:
                print(f"[warn] {fid}: cannot parse url {url}", file=sys.stderr)
                files_out.append(entry)
                continue

            if parsed and not args.from_local_only:
                repo_id, _rev, hf_path = parsed
                try:
                    meta = _hf_metadata(repo_id, hf_path, "main")
                    entry["repo_id"] = repo_id
                    entry["hf_path"] = hf_path
                    entry["revision"] = meta["revision"]
                    entry["size_bytes"] = meta["size_bytes"] or None
                    entry["sha256_hf"] = meta["sha256"]
                    entry["url"] = pinned_url(repo_id, entry["revision"], hf_path)
                    print(f"[hf] {fid} rev={entry['revision'][:12]}... size={entry.get('size_bytes')}")
                except Exception as e:
                    print(f"[err] {fid} HF: {e}", file=sys.stderr)

            # Local file = ground truth for the machine where tests passed
            if local.is_file():
                local_sha = sha256_file(local)
                local_size = local.stat().st_size
                entry["size_bytes"] = local_size
                entry["sha256"] = local_sha
                entry["verified_local"] = str(local)
                hf_sha = entry.pop("sha256_hf", None)
                if hf_sha and hf_sha != local_sha:
                    entry["sha256_mismatch_hf"] = hf_sha
                    print(f"[warn] {fid}: local sha != HF LFS sha", file=sys.stderr)
                print(f"[hash] {fid} from {local.name}")
            elif entry.get("sha256_hf"):
                entry["sha256"] = entry.pop("sha256_hf")

            files_out.append(entry)

    lock = {
        "lock_version": 1,
        "locked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "description": "Pinned model files for jinFrameComfyUI. Do not use resolve/main for installs.",
        "comfyui_root_default": str(Path(args.comfy_root).resolve()),
        "manifest_source": str(manifest_path.relative_to(REPO_ROOT)),
        "files": files_out,
    }

    out_path = lock_path()
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(lock, f, indent=2, ensure_ascii=False)
        f.write("\n")

    missing_sha = [e["id"] for e in files_out if not e.get("sha256")]
    if missing_sha:
        print(f"[warn] no sha256 for: {', '.join(missing_sha)}", file=sys.stderr)
    print(f"Wrote {out_path} ({len(files_out)} files)")
    return 0 if not missing_sha else 1


if __name__ == "__main__":
    raise SystemExit(main())
