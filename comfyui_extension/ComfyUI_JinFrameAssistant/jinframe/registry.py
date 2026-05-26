"""Model pack detection and downloads for JinFrame Assistant."""
from __future__ import annotations

import json
import os
import shutil
import sys
import threading
import urllib.request
from pathlib import Path
from typing import Any

_MANIFEST_PATH = Path(__file__).resolve().parent.parent / "models_manifest.json"
_DOWNLOAD_LOCK = threading.Lock()
_DOWNLOAD_STATE: dict[str, Any] = {"active": False, "items": {}, "error": None}


def _install_dir() -> Path:
    return repo_root() / "install"


def _ensure_lock_import() -> None:
    inst = _install_dir()
    if str(inst) not in sys.path:
        sys.path.insert(0, str(inst))


def comfy_models_root() -> Path:
    root = os.environ.get("COMFYUI_ROOT", r"C:\ComfyUI\ComfyUI")
    return Path(root).resolve() / "models"


def repo_root() -> Path:
    if os.environ.get("JINFRAME_REPO_ROOT"):
        return Path(os.environ["JINFRAME_REPO_ROOT"]).resolve()
    ext = Path(__file__).resolve().parent.parent
    for candidate in (ext.parent.parent, ext):
        if (candidate / "workflows").is_dir() or (candidate / "MODELS.lock.json").is_file():
            return candidate.resolve()
    return ext.resolve()


def _lock_path() -> Path:
    return repo_root() / "MODELS.lock.json"


def _load_lock() -> dict | None:
    p = _lock_path()
    if not p.is_file():
        return None
    with p.open(encoding="utf-8") as f:
        return json.load(f)


def _load_manifest() -> dict:
    with _MANIFEST_PATH.open(encoding="utf-8") as f:
        manifest = json.load(f)
    lock = _load_lock()
    if not lock:
        return manifest
    _ensure_lock_import()
    from models_lock import merge_manifest_with_lock  # noqa: WPS433

    return merge_manifest_with_lock(manifest, lock)


def _lock_entry(file_id: str) -> dict | None:
    lock = _load_lock()
    if not lock:
        return None
    for entry in lock.get("files", []):
        if entry.get("id") == file_id:
            return entry
    return None


def _file_ok(path: Path, finfo: dict) -> bool:
    le = _lock_entry(finfo.get("id", ""))
    if le and le.get("sha256"):
        _ensure_lock_import()
        from models_lock import verify_file  # noqa: WPS433

        ok, _ = verify_file(path, le)
        return ok
    min_mb = float(finfo.get("min_mb", 1))
    if not path.is_file():
        return False
    return path.stat().st_size >= int(min_mb * 1024 * 1024 * 0.85)


def _resolve_file(pack_id: str, finfo: dict) -> tuple[Path, bool]:
    models = comfy_models_root()
    rel = finfo.get("dir", "")
    name = finfo["name"]
    path = models / rel / name if rel else models / name
    ok = _file_ok(path, finfo)
    if not ok and pack_id == "ltx_cloud" and finfo["id"] == "ltx_distill_lora":
        repo_lora = repo_root() / "distill_loras" / name
        if _file_ok(repo_lora, finfo):
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
            if not ok and finfo["id"] == "ltx_distill_lora":
                repo_lora = repo_root() / "distill_loras" / finfo["name"]
                if repo_lora.is_file():
                    ok = True
            le = _lock_entry(finfo.get("id", ""))
            files.append(
                {
                    "id": finfo["id"],
                    "name": finfo["name"],
                    "installed": ok,
                    "size_gb": round(path.stat().st_size / 1e9, 2) if ok and path.is_file() else None,
                    "revision": (le or {}).get("revision"),
                    "locked": bool(le and le.get("sha256")),
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


def _verify_after_download(dest: Path, finfo: dict) -> None:
    le = _lock_entry(finfo.get("id", ""))
    if not le or not le.get("sha256"):
        return
    _ensure_lock_import()
    from models_lock import verify_file  # noqa: WPS433

    ok, msg = verify_file(dest, le)
    if not ok:
        try:
            if dest.is_file():
                dest.unlink()
            part = dest.with_suffix(dest.suffix + ".part")
            if part.is_file():
                part.unlink()
        except OSError:
            pass
        hint = ""
        if "size mismatch" in msg and finfo.get("id") == "flux_dev_fp8":
            hint = " Run: git pull (updates MODELS.lock.json for ~17GB FLUX fp8), then download again."
        raise RuntimeError(f"SHA256 verify failed for {finfo['id']}: {msg}.{hint}")


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
            le = _lock_entry(fid)
            url = (le or {}).get("url") or finfo.get("url") or ""
            if not url:
                if fid == "ltx_distill_lora":
                    src = repo_root() / "distill_loras" / finfo["name"]
                    dst = comfy_models_root() / finfo["dir"] / finfo["name"]
                    if src.is_file():
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        if not dst.exists():
                            shutil.copy2(src, dst)
                        _verify_after_download(dst, finfo)
                        _DOWNLOAD_STATE["items"][fid] = {"pct": 100, "done": True}
                continue
            dest = comfy_models_root() / finfo["dir"] / finfo["name"]
            if _file_ok(dest, finfo):
                _DOWNLOAD_STATE["items"][fid] = {"pct": 100, "skipped": True}
                continue
            _DOWNLOAD_STATE["items"][fid] = {"pct": 0}
            _download_one(url, dest, fid)
            _verify_after_download(dest, finfo)
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
