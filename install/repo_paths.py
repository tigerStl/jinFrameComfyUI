"""Shared paths for jinFrameComfyUI. Override with env COMFYUI_ROOT / JINFRAME_REPO_ROOT."""
from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(
    os.environ.get("JINFRAME_REPO_ROOT", Path(__file__).resolve().parents[1])
).resolve()

COMFY_ROOT = Path(
    os.environ.get("COMFYUI_ROOT", r"C:\ComfyUI\ComfyUI")
).resolve()

COMFY_WF = COMFY_ROOT / "user" / "default" / "workflows"
COMFY_MODELS = COMFY_ROOT / "models"
COMFY_CUSTOM_NODES = COMFY_ROOT / "custom_nodes"
COMFY_OUTPUT = COMFY_ROOT / "output"

# Legacy alias used in some scripts
REPO_WF = REPO_ROOT / "workflows"
DISTILL_LORAS = REPO_ROOT / "distill_loras"
