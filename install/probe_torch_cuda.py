"""Verify PyTorch CUDA (same checks ComfyUI uses at startup)."""
import json
import os
import sys
import warnings
from pathlib import Path

try:
    import torch
except ImportError:
    sys.exit(3)


def _read_expected_min_major() -> int:
    env = os.environ.get("JINFRAME_MIN_CUDA_MAJOR", "").strip()
    if env.isdigit():
        return int(env)
    repo = os.environ.get("JINFRAME_REPO_ROOT", "").strip()
    if repo:
        p = Path(repo) / "jinframe_gpu_profile.json"
        if p.is_file():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                m = data.get("min_cuda_major")
                if m is not None:
                    return int(m)
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
    return 13


def _cuda_build_major() -> int:
    v = getattr(torch.version, "cuda", None) or ""
    try:
        return int(str(v).split(".")[0])
    except (ValueError, IndexError):
        return 0


def _probe_cuda_runtime(tag: str) -> int:
    """Return exit code when cuda.is_available() is False (1 generic, 6 driver/runtime)."""
    msg_parts: list[str] = []
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            torch.cuda.device_count()
        except Exception as exc:
            msg_parts.append(str(exc))

    blob = " ".join(msg_parts) + " ".join(str(w.message) for w in caught)
    lower = blob.lower()
    if "cudaerrornotsupported" in lower or "older driver" in lower:
        print("torch", tag, "- CUDA runtime not supported by current NVIDIA driver.")
        if "+cu130" in tag:
            print("FIX: Update GeForce driver to 580.0 or newer, reboot, then re-run repair_comfyui_cuda.ps1")
            print("     (cu130 wheel is correct; do NOT downgrade to cu128 on RTX 3050.)")
        else:
            print("FIX: Update NVIDIA driver, reboot, then re-run install_pytorch_cuda.ps1 -Force")
        return 6

    if "gpu is lost" in lower or "unknown error" in lower:
        print("torch", tag, "- GPU/driver unstable. Reboot and verify nvidia-smi first.")
        return 5

    print("torch.cuda.is_available() is False", tag)
    if "+cu130" in tag:
        print("If nvidia-smi works: update driver to 580+, reboot, run repair_comfyui_cuda.ps1")
    return 1


min_major = _read_expected_min_major()
tag = getattr(torch, "__version__", "?")

if min_major >= 13 and "+cu130" not in tag:
    if "+cu128" in tag:
        print(
            "torch",
            tag,
            "- RTX 3050/30-40 need cu130, not cu128. Run: install_pytorch_cuda.ps1 -Force",
        )
    else:
        print("torch", tag, "- need +cu130 (run install_pytorch_cuda.ps1 -Force)")
    sys.exit(4)

if min_major < 13 and "+cu128" not in tag:
    if "+cu130" in tag:
        print("torch", tag, "- RTX 50 needs cu128 nightly. Run: install_pytorch_cuda.ps1 -Force")
    else:
        print("torch", tag, "- need +cu128 nightly for RTX 50")
    sys.exit(4)

if not torch.cuda.is_available():
    sys.exit(_probe_cuda_runtime(tag))

cuda_ver = getattr(torch.version, "cuda", None)
if not cuda_ver:
    print("torch built without CUDA", tag)
    sys.exit(2)

major = _cuda_build_major()
if major < min_major:
    print("torch", tag, "cuda", cuda_ver, f"- need CUDA>={min_major}.0")
    sys.exit(4)

try:
    dev = torch.cuda.current_device()
    name = torch.cuda.get_device_name(dev)
except Exception as exc:
    print("cuda init failed (ComfyUI will crash):", exc)
    print("torch", tag, "cuda", cuda_ver)
    sys.exit(5)

print("torch", tag, "cuda", cuda_ver, "device", dev, name)
sys.exit(0)
