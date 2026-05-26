"""Load MODELS.lock.json — pinned HF revisions and SHA256 for reproducible installs."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent
_LOCK_PATH = REPO_ROOT / "MODELS.lock.json"
_HF_RESOLVE_RE = re.compile(
    r"https://huggingface\.co/(?P<repo>[^/]+/[^/]+)/resolve/(?P<rev>[^/]+)/(?P<path>.+)$"
)


def lock_path() -> Path:
    return _LOCK_PATH


def load_lock() -> dict:
    if not _LOCK_PATH.is_file():
        raise FileNotFoundError(f"Missing {_LOCK_PATH.name}; run: python install/generate_models_lock.py")
    with _LOCK_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def parse_hf_url(url: str) -> tuple[str, str, str] | None:
    m = _HF_RESOLVE_RE.match(url.strip())
    if not m:
        return None
    return m.group("repo"), m.group("rev"), m.group("path")


def pinned_url(repo_id: str, revision: str, filename: str) -> str:
    return f"https://huggingface.co/{repo_id}/resolve/{revision}/{filename}"


def file_entry_by_id(lock: dict, file_id: str) -> dict | None:
    for entry in lock.get("files", []):
        if entry.get("id") == file_id:
            return entry
    return None


def all_file_entries(lock: dict) -> list[dict]:
    return list(lock.get("files", []))


def sha256_file(path: Path, chunk_mb: int = 8) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            block = f.read(chunk_mb * 1024 * 1024)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def verify_file(path: Path, entry: dict) -> tuple[bool, str]:
    if not path.is_file():
        return False, "missing"
    size = path.stat().st_size
    expected_sha = (entry.get("sha256") or "").lower()
    alt_sha = (entry.get("sha256_mismatch_hf") or "").lower()

    if expected_sha:
        actual = sha256_file(path)
        if actual == expected_sha:
            return True, "ok"
        if alt_sha and actual == alt_sha:
            return True, "ok (hf-updated blob)"
        if expected_sha and actual != expected_sha:
            return False, "sha256 mismatch"

    expected_size = entry.get("size_bytes")
    if expected_size and size != expected_size:
        if expected_sha:
            return False, f"size mismatch (have {size}, want {expected_size}); sha256 also failed"
        return False, f"size mismatch (have {size}, want {expected_size})"

    if entry.get("min_mb"):
        min_bytes = int(float(entry["min_mb"]) * 1024 * 1024 * 0.85)
        if size < min_bytes:
            return False, "smaller than min_mb threshold"
    return True, "ok"


def merge_manifest_with_lock(manifest: dict, lock: dict) -> dict:
    """Return manifest packs with per-file pinned url/revision/sha256 from lock."""
    lock_by_id = {e["id"]: e for e in lock.get("files", []) if e.get("id")}
    out = json.loads(json.dumps(manifest))
    for pack in out.get("packs", []):
        for finfo in pack.get("files", []):
            le = lock_by_id.get(finfo.get("id"))
            if not le:
                continue
            for key in ("revision", "sha256", "size_bytes", "url", "repo_id", "hf_path", "source"):
                if key in le and le[key] not in (None, ""):
                    finfo[key] = le[key]
    out["lock_version"] = lock.get("lock_version")
    out["locked_at"] = lock.get("locked_at")
    return out
