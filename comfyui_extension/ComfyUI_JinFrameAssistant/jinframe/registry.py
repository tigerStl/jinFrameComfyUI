"""Model pack detection and downloads for JinFrame Assistant."""
from __future__ import annotations

import json
import os
import shutil
import threading
import urllib.request
from pathlib import Path
from typing import Any

_MANIFEST_PATH = Path(__file__).resolve().parent.parent / "models_manifest.json"
_DOWNLOAD_LOCK = threading.Lock()
_DOWNLOAD_STATE: dict[str, Any] = {"active": False, "items": {}, "error": None}


def comfy_models_root() -> Path:
    root = os.environ.get("COMFYUI_ROOT", r"C:\ComfyUI\ComfyUI")
    return Path(root).resolve() / "models"


def repo_root() -> Path:
    if os.environ.get("JINFRAME_REPO_ROOT"):
        return Path(os.environ["JINFRAME_REPO_ROOT"]).resolve()
    ext = Path(__file__).resolve().parent.parent
    for candidate in (
        Path(r"c:\tiger\videoModel\jinFrameComfyUI"),
        ext.parent.parent,
        ext,
    ):
        if (candidate / "workflows").is_dir():
            return candidate.resolve()
    return ext.resolve()


def _load_manifest() -> dict:
    with _MANIFEST_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _file_ok(path: Path, min_mb: float) -> bool:
    if not path.is_file():
        return False
    return path.stat().st_size >= int(min_mb * 1024 * 1024 * 0.85)


def _resolve_file(pack_id: str, finfo: dict) -> tuple[Path, bool]:
    models = comfy_models_root()
    rel = finfo.get("dir", "")
    name = finfo["name"]
    path = models / rel / name if rel else models / name
    min_mb = float(finfo.get("min_mb", 1))
    ok = _file_ok(path, min_mb)
    if not ok and pack_id == "ltx_cloud" and finfo["id"] == "ltx_distill_lora":
        repo_lora = repo_root() / "distill_loras" / name
        if _file_ok(repo_lora, min_mb):
            ok = True
            path = repo_lora
    return path, ok


def scan_packs() -> list[dict]:
    data = _load_manifest()
    out = []
    for pack in data.get("packs", []):
        files = []
        missing = 0
        for finfo in pack.get("files", []):
            path, ok = _resolve_file(pack["id"], finfo)
            if not ok and not finfo.get("url"):
                if finfo["id"] == "ltx_distill_lora":
                    repo_lora = repo_root() / "distill_loras" / finfo["name"]
                    if repo_lora.is_file():
                        ok = True
            files.append(
                {
                    "id": finfo["id"],
                    "name": finfo["name"],
                    "installed": ok,
                    "size_gb": round(path.stat().st_size / 1e9, 2) if ok and path.is_file() else None,
                }
            )
            if not ok:
                missing += 1
        out.append(
            {
                "id": pack["id"],
                "label_zh": pack.get("label_zh", pack["id"]),
                "label_en": pack.get("label_en", pack["id"]),
                "workflow_hint": pack.get("workflow_hint", ""),
                "note_zh": pack.get("note_zh", ""),
                "files": files,
                "missing_count": missing,
                "all_installed": missing == 0,
            }
        )
    return out


def _download_one(url: str, dest: Path, item_id: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": "JinFrameAssistant/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp, part.open("wb") as f:
        total = int(resp.headers.get("content-length", 0) or 0)
        done = 0
        while True:
            chunk = resp.read(8 * 1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            pct = int(done * 100 / total) if total else 0
            _DOWNLOAD_STATE["items"][item_id] = {"pct": pct, "done_mb": done // (1024 * 1024)}
    if dest.exists():
        dest.unlink()
    shutil.move(str(part), str(dest))
    _DOWNLOAD_STATE["items"][item_id] = {"pct": 100, "done": True}


def _run_downloads(file_ids: list[str]) -> None:
    global _DOWNLOAD_STATE
    data = _load_manifest()
    id_to_file: dict[str, tuple[dict, dict]] = {}
    for pack in data.get("packs", []):
        for finfo in pack.get("files", []):
            id_to_file[finfo["id"]] = (pack, finfo)

    try:
        for fid in file_ids:
            if fid not in id_to_file:
                continue
            pack, finfo = id_to_file[fid]
            url = finfo.get("url") or ""
            if not url:
                if fid == "ltx_distill_lora":
                    src = repo_root() / "distill_loras" / finfo["name"]
                    dst = comfy_models_root() / finfo["dir"] / finfo["name"]
                    if src.is_file():
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        if not dst.exists():
                            shutil.copy2(src, dst)
                        _DOWNLOAD_STATE["items"][fid] = {"pct": 100, "done": True}
                continue
            path, ok = _resolve_file(pack["id"], finfo)
            dest = comfy_models_root() / finfo["dir"] / finfo["name"]
            if ok and _file_ok(dest, finfo.get("min_mb", 1)):
                _DOWNLOAD_STATE["items"][fid] = {"pct": 100, "skipped": True}
                continue
            _DOWNLOAD_STATE["items"][fid] = {"pct": 0}
            _download_one(url, dest, fid)
    except Exception as e:
        _DOWNLOAD_STATE["error"] = str(e)
    finally:
        _DOWNLOAD_STATE["active"] = False


def start_downloads(pack_ids: list[str] | None = None, file_ids: list[str] | None = None) -> dict:
    with _DOWNLOAD_LOCK:
        if _DOWNLOAD_STATE.get("active"):
            return {"started": False, "reason": "already_downloading"}
        _DOWNLOAD_STATE.clear()
        _DOWNLOAD_STATE.update({"active": True, "items": {}, "error": None})

    to_fetch: list[str] = list(file_ids or [])
    if pack_ids:
        data = _load_manifest()
        for pack in data.get("packs", []):
            if pack["id"] in pack_ids:
                for finfo in pack.get("files", []):
                    if finfo["id"] not in to_fetch:
                        to_fetch.append(finfo["id"])

    threading.Thread(target=_run_downloads, args=(to_fetch,), daemon=True).start()
    return {"started": True, "file_ids": to_fetch}


def download_status() -> dict:
    return dict(_DOWNLOAD_STATE)
