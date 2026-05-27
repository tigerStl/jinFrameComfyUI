"""Optional file logging for JinFrame Assistant (testing / WinError 10038 diagnosis)."""
from __future__ import annotations

import json
import os
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()
_LOG_PATH: Path | None = None


def _default_log_dir() -> Path:
    env = os.environ.get("JINFRAME_LOG_DIR", "").strip()
    if env:
        return Path(env)
    if os.name == "nt":
        return Path(r"K:\temp")
    return Path(os.environ.get("TEMP") or os.environ.get("TMP") or ".")


def log_enabled() -> bool:
    """Default on (opt-out with JINFRAME_DEBUG_LOG=0). Writes under K:\\temp on Windows."""
    v = os.environ.get("JINFRAME_DEBUG_LOG", "").strip().lower()
    if v in ("0", "false", "no", "off"):
        return False
    return True


def log_file_path() -> Path | None:
    global _LOG_PATH
    if not log_enabled():
        return None
    if _LOG_PATH is None:
        name = os.environ.get("JINFRAME_LOG_FILE", "jinframe_assistant.log").strip()
        _LOG_PATH = _default_log_dir() / name
    return _LOG_PATH


def _mask_secrets(obj: Any) -> Any:
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            lk = str(k).lower()
            if "key" in lk or "token" in lk or "password" in lk or "secret" in lk:
                if isinstance(v, str) and v:
                    out[k] = f"<redacted len={len(v)} suffix={v[-4:] if len(v) >= 4 else '****'}>"
                else:
                    out[k] = "<redacted>"
            else:
                out[k] = _mask_secrets(v)
        return out
    if isinstance(obj, list):
        return [_mask_secrets(x) for x in obj]
    return obj


def log_event(event: str, **fields: Any) -> None:
    path = log_file_path()
    if path is None:
        return
    row = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **_mask_secrets(fields),
    }
    line = json.dumps(row, ensure_ascii=False, default=str) + "\n"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with _LOCK:
            with path.open("a", encoding="utf-8") as f:
                f.write(line)
    except OSError:
        pass


def log_exception(event: str, exc: BaseException, **fields: Any) -> None:
    log_event(
        event,
        error=str(exc),
        error_type=type(exc).__name__,
        traceback=traceback.format_exc(),
        **fields,
    )
