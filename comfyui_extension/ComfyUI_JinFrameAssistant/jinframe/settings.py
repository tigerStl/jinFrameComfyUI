"""Persist Cursor API key under ComfyUI user folder (local only)."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

_CONFIG_NAME = "jinframe_assistant_config.json"


def _config_path() -> Path:
    root = Path(os.environ.get("COMFYUI_ROOT", r"C:\ComfyUI\ComfyUI"))
    return root / "user" / "default" / _CONFIG_NAME


def load_config() -> dict[str, Any]:
    path = _config_path()
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_config(patch: dict[str, Any]) -> dict[str, Any]:
    data = load_config()
    data.update(patch)
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def mask_key(key: str) -> str:
    key = (key or "").strip()
    if len(key) <= 8:
        return "****" if key else ""
    return key[:4] + "…" + key[-4:]


def get_api_key(override: str | None = None) -> str:
    if override and override.strip():
        return override.strip()
    env = os.environ.get("CURSOR_API_KEY", "").strip()
    if env:
        return env
    return str(load_config().get("cursor_api_key", "")).strip()


def public_settings() -> dict[str, Any]:
    cfg = load_config()
    key = get_api_key()
    return {
        "agent_enabled_default": bool(cfg.get("agent_enabled", False)),
        "has_key": bool(key),
        "key_masked": mask_key(key),
        "config_path": str(_config_path()),
    }
