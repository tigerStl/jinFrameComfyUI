"""Windows fix for cursor-sdk Bridge.launch WinError 10038.

cursor_sdk._bridge._read_discovery registers a PIPE fd on selectors.DefaultSelector,
which calls select() on Windows — only valid for sockets, not pipes → WinError 10038.
Replace the wait loop with time.sleep polling (drain_available already uses os.read).
"""
from __future__ import annotations

import os
import sys
import time

_PATCHED = False


def apply_cursor_sdk_windows_patch() -> bool:
    global _PATCHED
    if _PATCHED or os.name != "nt":
        return _PATCHED
    try:
        import cursor_sdk._bridge as bridge_mod
    except ImportError:
        return False

    if getattr(bridge_mod._read_discovery, "_jinframe_patched", False):
        _PATCHED = True
        return True

    _orig = bridge_mod._read_discovery

    def _read_discovery_win_safe(process, timeout: float):
        import codecs

        from cursor_sdk.errors import CursorSDKError

        from cursor_sdk._bridge import parse_discovery_line

        if process.stderr is None:
            raise CursorSDKError("Bridge process stderr is unavailable")
        stderr_fd = process.stderr.fileno()
        was_blocking = os.get_blocking(stderr_fd)
        os.set_blocking(stderr_fd, False)
        try:
            decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
            deadline = time.monotonic() + timeout
            stderr_lines: list[str] = []
            pending = ""

            def drain_available():
                nonlocal pending
                while True:
                    try:
                        chunk = os.read(stderr_fd, 8192)
                    except BlockingIOError:
                        return None
                    if not chunk:
                        final_text = decoder.decode(b"", final=True)
                        if final_text:
                            pending += final_text
                        if pending:
                            line = pending
                            pending = ""
                            stderr_lines.append(line)
                            return parse_discovery_line(line)
                        return None
                    pending += decoder.decode(chunk)
                    while "\n" in pending:
                        line, pending = pending.split("\n", 1)
                        line += "\n"
                        stderr_lines.append(line)
                        discovery = parse_discovery_line(line)
                        if discovery is not None:
                            return discovery

            while time.monotonic() < deadline:
                discovery = drain_available()
                if discovery is not None:
                    return discovery
                exit_code = process.poll()
                if exit_code is not None:
                    discovery = drain_available()
                    if discovery is not None:
                        return discovery
                    raise CursorSDKError(
                        f"Bridge exited before discovery with status {exit_code}: "
                        + "".join(stderr_lines)
                        + pending
                    )
                time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))
            raise CursorSDKError("Timed out waiting for bridge discovery")
        finally:
            os.set_blocking(stderr_fd, was_blocking)

    _read_discovery_win_safe._jinframe_patched = True  # type: ignore[attr-defined]
    bridge_mod._read_discovery = _read_discovery_win_safe
    _PATCHED = True
    return True


def patch_status() -> dict[str, object]:
    return {
        "windows": os.name == "nt",
        "applied": _PATCHED,
        "python": sys.executable,
    }
